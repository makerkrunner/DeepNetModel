# -*- coding: utf-8 -*-
import argparse

import numpy as np
import time
import torch
import visdom
import os

from torch import optim

from lstm_pytorch import MLSTMCell, MovingMNISTLoader, crossentropyloss, MCLSTMCell, MResCLSTMCell

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='training parameter setting')
    parser.add_argument('--use_cuda', type=bool, default=False, help='use cuda [ False ]')
    parser.add_argument('--use_visdom', type=bool, default=True, help='use visdom [ False ]')
    parser.add_argument('--save_epoch', type=int, default=-1, help='save model after epoch [ 1 ]')
    args = parser.parse_args()

    use_cuda = args.use_cuda
    use_visdom = args.use_visdom


    # --------------2层CLSTMCell实验相关----------------
    batch_size = 1
    input_shape = (64, 64) # H, W
    input_channels = 1
    i2s_filter_size = 5
    # s2s_filter_size_list = [5, 5]
    # num_features_list = [64, 64]
    s2s_filter_size_list = [3, 3]
    num_features_list = [16, 16]
    num_layers = len(s2s_filter_size_list)
    assert len(s2s_filter_size_list)==num_layers
    assert len(num_features_list)==num_layers

    model = MResCLSTMCell(input_shape, input_channels, i2s_filter_size, s2s_filter_size_list, num_features_list, num_layers)
    # model = ResCLSTM(input_shape, input_channels, 1)
    if use_cuda:
        model.cuda()

    local_path = os.path.expanduser('~/Data/mnist_test_seq.npy')
    train_dst = MovingMNISTLoader(local_path, split='train')
    train_loader = torch.utils.data.DataLoader(train_dst, batch_size=batch_size, shuffle=True)

    optimizer = optim.RMSprop(model.parameters(), lr=0.01, weight_decay=0.9)
    # optimizer = optim.Adam(model.parameters(), lr=0.0002, weight_decay=0.9)

    init_states = None
    if init_states is None:
        init_states = model.init_hidden(batch_size, use_cuda)

    if use_visdom:
        vis = visdom.Visdom()
        vis.close()

    init_time = str(int(time.time()))
    loss_iteration_save_file = '/tmp/loss_iteration_{}.txt'.format(init_time)
    loss_iteration_save_fp = open(loss_iteration_save_file, 'wb')

    data_count = int(train_dst.__len__() * 1.0 / batch_size)
    for epoch in range(1, 1000, 1):
        loss_epoch = 0
        for i, train_data in enumerate(train_loader):
            imgs = train_data[:, 0:10, ...]
            labels = train_data[:, 10:20, ...]
            if use_cuda:
                imgs = imgs.cuda()
                labels = labels.cuda()
            imgs_transpose = imgs.transpose(0, 1)
            # print('imgs_transpose.shape:', imgs_transpose.shape)
            # print('labels.shape:', labels.shape)
            outputs = model(imgs_transpose, init_states)
            # hidden_h, hidden_c = outputs[0][num_layers-1]
            # print('hidden_h.shape:', hidden_h.shape)
            # print('hidden_c.shape:', hidden_c.shape)
            last_hidden = outputs
            print('last_hidden.shape:', last_hidden.shape)

            optimizer.zero_grad()

            loss = 0
            for seq in range(10):
                predframe = torch.sigmoid(last_hidden[seq].view(batch_size, -1))
                labelframe = labels[:, seq, ...].view(batch_size, -1)
                # print('predframe.shape:', predframe.shape)
                # print('labelframe.shape:', labelframe.shape)
                loss += crossentropyloss(predframe, labelframe)

            loss.backward()
            optimizer.step()

            loss_np = loss.cpu().data.numpy() * 1.0 / batch_size
            print "loss:", loss_np
            loss_epoch += loss_np
            loss_iteration_save_fp.write(str(loss_np)+'\n')

            if use_visdom:
                win = 'loss_iteration'
                loss_np_expand = np.expand_dims(loss_np, axis=0)
                win_res = vis.line(X=np.ones(1) * (i + data_count * (epoch - 1) + 1), Y=loss_np_expand, win=win, update='append')
                if win_res != win:
                    vis.line(X=np.ones(1) * (i + data_count * (epoch - 1) + 1), Y=loss_np_expand, win=win, opts=dict(title=win, xlabel='iteration', ylabel='loss'))
            # break

        loss_avg_epoch = loss_epoch / (data_count * 1.0)
        if use_visdom:
            win = 'loss_epoch'
            loss_avg_epoch_expand = np.expand_dims(loss_avg_epoch, axis=0)
            win_res = vis.line(X=np.ones(1)*epoch, Y=loss_avg_epoch_expand, win=win, update='append')
            if win_res != win:
                vis.line(X=np.ones(1)*epoch, Y=loss_avg_epoch_expand, win=win, opts=dict(title=win, xlabel='epoch', ylabel='loss'))

    loss_iteration_save_fp.close()
    # --------------2层CLSTMCell实验相关----------------

