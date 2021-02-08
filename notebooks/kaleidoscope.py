import numpy as np
import tensorflow.compat.v1 as tf

def kaleidoscope_lp(x, h0, adj,
                    labels=None,
                    num_parallel_runs=1,
                    beta=100.0,
                    seed=0,
                    normalize=True,
                    render_func=None,
                    error_func=None,
                    num_iters=20,
                    random_init=True,
                    excite=True,
                    inhibit=True,
                    push=True,
                    smooth=True,
                    damp=True,
                    error_fb=False,
                    **kwargs):
    '''
    x: feedforward drive [B,N,C]
    h0: initial hidden state [B,N,D]
    adj: excitatory connections [B,N,N] in [0.,1.]
    '''
    B,N,Q = h0.shape.as_list()
    P = num_parallel_runs
    BP = B*P

    # frequent funcs
    _tr = lambda t: tf.transpose(t, [0,2,1])
    _norm = lambda t: tf.nn.l2_normalize(t, axis=-1, epsilon=1e-8) if normalize else tf.identity

    # if running multiple copies in parallel

    if P > 1:
        def ptile(t):
            shape = t.shape.as_list()[1:]
            return tf.reshape(tf.tile(t[:,None], [1,P]+[1]*len(shape)), [BP]+shape)
        x = ptile(x)
        h0 = ptile(h0)
        adj = ptile(adj)

    # figure out which nodes are valid.
    # by convention, invalid nodes should be initialized to sum == 0 on last dim.
    valid = tf.cast(tf.reduce_sum(h0, axis=-1, keepdims=True) > 0.1, tf.float32)
    valid_adj = valid * tf.transpose(valid, [0,2,1])

    # create the excitatory and inhibitory affinity matrices.
    # by convention, affinity values that are exactly 0 are masked out
    # this allows passing of sparse, local connectivity matrices
    adj_mask = tf.cast(adj > 0.0, tf.float32) # [BP,N,N]
    adj_e = adj * valid_adj * adj_mask # [BP,N,N]
    adj_i = (1.0 - adj) * valid_adj * adj_mask # [BP,N,N]
    adj_e2 = tf.matmul(adj_e, adj_e) * valid_adj # can be less local

    # randomly initialize the active nodes
    probs = valid / tf.maximum(1., tf.reduce_sum(valid, axis=[1,2], keepdims=True))
    dist = tf.distributions.Categorical(probs=probs[:,:,0], dtype=tf.int32)
    init_inds = dist.sample()
    activated = tf.cast(tf.one_hot(init_inds, depth=N, axis=-1)[...,None], tf.float32) # [B,N,1]

    # initial state
    h = h0

    # iterate
    for it in range(num_iters):
        # how many sender neurons
        n_senders_e = tf.maximum(1., tf.reduce_sum(adj_e * activated, axis=-2, keepdims=True)) # [B,1,N]
        n_senders_i = tf.maximum(1., tf.reduce_sum(adj_i * activated, axis=-2, keepdims=True)) # [B,1,N]

        # excitatory effects smooth out labels within connected nodes
        if excite:
            e_effects = tf.matmul(_tr(h), adj_e * activated) / n_senders_e
            h += _tr(e_effects)

        # inhibitory effects make disconnected nodes more orthogonal
        if inhibit:
            i_effects = tf.matmul(_tr(h), adj_i * activated) / n_senders_i
            h -= _tr(i_effects)

        # normalize
        h = _norm(h)

        # update which nodes are activated




    return init_inds

if __name__ == '__main__':
    B,N,D = [4,256,10]
    x = tf.random.uniform([B,N,D], dtype=tf.float32)
    x = tf.nn.l2_normalize(x, axis=-1)
    h0 = x
    adj = tf.ones([B,N,N], dtype=tf.float32)

    inds = kaleidoscope_lp(x,h0,adj, num_parallel_runs=3)

    sess = tf.Session()
    _inds = sess.run(inds)
    print(_inds)
