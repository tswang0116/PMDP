import os
import errno
import torch
import numpy as np


def calc_hamming(B1, B2):
    num = B1.shape[0]
    q = B1.shape[1]
    result = torch.zeros(num).cuda()
    for i in range(num):
        result[i] = 0.5 * (q - B1[i].dot(B2[i]))
    return result


def calc_hamming_dist(B1, B2):
    q = B2.shape[1]
    if len(B1.shape) < 2:
        B1 = B1.unsqueeze(0)
    distH = 0.5 * (q - B1.mm(B2.transpose(0, 1)))
    return distH


def CalcMap(qB, rB, query_label, retrieval_label, k=None):
    num_query = query_label.shape[0]
    map = 0.
    if k is None:
        k = retrieval_label.shape[0]
    for i in range(num_query):
        gnd = (query_label[i].unsqueeze(0).mm(retrieval_label.t()) > 0).type(torch.float).squeeze()
        tsum = torch.sum(gnd)
        if tsum == 0:
            continue
        hamm = calc_hamming_dist(qB[i, :], rB)
        _, ind = torch.sort(hamm)
        ind.squeeze_()
        gnd = gnd[ind]
        total = min(k, int(tsum))
        count = torch.arange(1, total + 1).type(torch.float).to(gnd.device)
        tindex = torch.nonzero(gnd)[:total].squeeze().type(torch.float) + 1.0
        map += torch.mean(count / tindex)
    map = map / num_query
    return map


def CalcPSR(TqB, IqB, IdB, k=None):
    num_query = TqB.shape[0]
    rB = torch.cat((IqB, IdB), dim=0)
    num_psr= 0.
    for i in range(num_query):
        hamm = calc_hamming_dist(TqB[i, :], rB)
        _, ind = torch.sort(hamm)
        ind.squeeze_()
        if i not in ind[:k]:
            num_psr = num_psr + 1
    psr = num_psr / num_query
    return psr


def return_results(index, qB, rB, near=None, rank=None):
    num_query = qB.shape[0]
    index_matrix = torch.zeros(num_query, 1+near+rank).int().cuda()
    index = torch.from_numpy(index).cuda()
    for i in range(num_query):
        hamm = calc_hamming_dist(qB[i, :], rB)
        _, ind = torch.sort(hamm)
        ind.squeeze_()
        index_matrix[i] = torch.cat((index[i].unsqueeze(0), ind[:near], ind[np.linspace(0, rB.shape[0]-1, rank).astype('int')]), 0)
    return index_matrix


def image_normalization(_input):
    _input = 2 * _input / 255 - 1
    return _input


def image_restoration(_input):
    _input = (_input + 1) / 2 * 255
    return _input


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise