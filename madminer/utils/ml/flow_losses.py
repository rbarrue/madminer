from __future__ import absolute_import, division, print_function

import torch
from torch.nn.modules.loss import MSELoss


def negative_log_likelihood(log_p_pred, t_pred, t_true):
    """

    Parameters
    ----------
    log_p_pred :
        
    t_pred :
        
    t_true :
        

    Returns
    -------

    """
    return -torch.mean(log_p_pred)


def score_mse(log_p_pred, t_pred, t_true):
    """

    Parameters
    ----------
    log_p_pred :
        
    t_pred :
        
    t_true :
        

    Returns
    -------

    """
    return MSELoss()(t_pred, t_true)
