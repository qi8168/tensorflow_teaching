import tensorflow as tf
import numpy as np
import argparse
import os


class Config:
    def __init__(self):
        self.batch_size = 2
        self.num_step = 8 * 4
        self.num_units = 5
        self.gpus = self.get_gpus()
        self.classes = 4
        self.ch_size = 200

        self.name = 'p25'
        self.save_path = 'models/{name}/{name}'.format(name=self.name)
        self.logdir = 'logs/{name}/'.format(name=self.name)

        self.lr = 0.0002
        self.epoches = 100

    def get_gpus(self):
        value = os.getenv('CUDA_VISIBLE_DEVICES', '0')
        return len(value.split(','))

    def from_cmd_line(self):
        parser = argparse.ArgumentParser()
        for name in dir(self):
            value = getattr(self, name)
            if type(value) in (int, float, bool, str) and not name.startswith('__'):
                parser.add_argument('--' + name, default=value, help='Default to %s' % value, type=type(value))
        a = parser.parse_args()
        for name in dir(self):
            value = getattr(self, name)
            if type(value) in (int, float, bool, str) and not name.startswith('__') and hasattr(a, name):
                value = getattr(a, name)
                setattr(self, name, value)


class Tensors:
    def __init__(self, config: Config):
        self.config = config
        self.sub_ts = []

        with tf.device('/gpu:0'):
            self.lr = tf.placeholder(tf.float32, [], 'lr')
            opt = tf.train.AdamOptimizer(self.lr)

        with tf.variable_scope('poem'):
            for gpu_index in range(config.gpus):
                self.sub_ts.append(SubTensors(config, gpu_index, opt))
                tf.get_variable_scope().reuse_variables()

        with tf.device('/gpu:0'):
            grad = self.merge_grads()

            self.train_op = opt.apply_gradients(grad)
            self.loss = tf.reduce_mean([ts.loss for ts in self.sub_ts])

            tf.summary.scalar('loss', self.loss)
            self.summary_op = tf.summary.merge_all()

    def merge_grads(self):
        indexed_grads = {}
        grads = {}
        for ts in self.sub_ts:
            for g, v in ts.grad:
                if isinstance(g, tf.IndexedSlices):
                    if not v in indexed_grads:
                        indexed_grads[v] = []
                    indexed_grads[v].append(g)
                else:
                    if not v in grads:
                        grads[v] = []
                    grads[v].append(g)
        # grads = { v1: [g11, g12, g13, ...], v2:[g21, g22, ...], ....}
        grads = [(tf.reduce_mean(grads[v], axis=0), v) for v in grads]

        for v in indexed_grads:
            indices = tf.concat([g.indices for g in indexed_grads[v]], axis=0)
            values = tf.concat([g.values for g in indexed_grads[v]], axis=0)
            g = tf.IndexedSlices(values, indices)
            grads.append((g, v))

        return grads


class SubTensors:
    def __init__(self, config, gpu_index, opt):
        with tf.device('/gpu:%d' % gpu_index):
            self.x = tf.placeholder(tf.int32, [None, config.num_step], 'x')

            # word2vec
            ch_dict = tf.get_variable('ch_dict', [config.ch_size, config.num_units], tf.float32)
            x = tf.nn.embedding_lookup(ch_dict, self.x)  # [-1, num_step, num_units]

            self.y = tf.placeholder(tf.int32, [None, config.num_step], 'y')
            y = tf.one_hot(self.y, config.classes)  # [-1, num_step, classes]

            losses, self.y_predict = self.bi_rnn(x, y, config)

            self.loss = tf.reduce_mean(losses)
            self.grad = opt.compute_gradients(self.loss)  # [(g1, v1), (g2, v2), ... , (gn, vn)]


    def bi_rnn(self, x, y, config):
        cell1 = tf.nn.rnn_cell.BasicLSTMCell(config.num_units, state_is_tuple=True, name='lstm1')
        cell2 = tf.nn.rnn_cell.BasicLSTMCell(config.num_units, state_is_tuple=True, name='lstm2')

        batch_size_ts = tf.shape(x)[0]
        state1 = cell1.zero_state(batch_size_ts, tf.float32)  # [batch_size, state_size]
        state2 = cell2.zero_state(batch_size_ts, tf.float32)  # [batch_size, state_size]

        losses = []
        y_predict = []

        y1_pred = []
        y2_pred = []
        with tf.variable_scope('rnn'):

            for i in range(config.num_step):
                xi1 = x[:, i, :]  # [-1, num_units]
                yi1_pred, state1 = cell1(xi1, state1)  # [-1, num_units]
                y1_pred.append(yi1_pred)

                xi2 = x[:, config.num_step - i - 1, :]
                yi2_pred, state2 = cell2(xi2, state2)  # [-1, num_units]
                y2_pred.insert(0, yi2_pred)
                tf.get_variable_scope().reuse_variables()   # ******

        with tf.variable_scope('rnn'):
            for i in range(config.num_step):
                yi_pred = tf.layers.dense(y1_pred[i] + y2_pred[i], config.classes, name='yi_dense')  # [-1, ch_size]

                y_predict.append(tf.argmax(yi_pred, axis=1, output_type=tf.int32))  # [-1, num_step]

                yi = y[:, i, :]  # [-1, classes]

                loss_i = tf.nn.softmax_cross_entropy_with_logits_v2(labels=yi, logits=yi_pred)
                losses.append(loss_i)
                tf.get_variable_scope().reuse_variables()

        return losses, y_predict


class Samples:
    def __init__(self, config: Config):
        self.config = config
        self.index = 0
        self.data = list(np.random.randint(0, config.ch_size, size=[self.num(), config.num_step]))
        self.label = list(np.random.randint(0, config.classes, size=[self.num(), config.num_step]))

    def num(self):
        """
        The number of the samples in total.
        :return:
        """
        return 100

    def next_batch(self, batch_size):
        next = self.index + batch_size
        if next < self.num():
            result0 = self.data[self.index: next]
            result1 = self.label[self.index: next]
        else:
            result0 = self.data[self.index:]
            result1 = self.label[self.index:]
            next -= self.num()
            result0 += self.data[:next]
            result1 += self.label[:next]
        self.index = next
        return result0, result1  # [batch_size, num_step], [batch_size, num_step]


class App:
    def __init__(self, config: Config):
        self.config = config
        graph = tf.Graph()
        with graph.as_default():
            self.samples = Samples(config)
            self.tensors = Tensors(config)
            cfg = tf.ConfigProto()
            cfg.allow_soft_placement = True
            self.session = tf.Session(config=cfg, graph=graph)
            self.saver = tf.train.Saver()
            try:
                self.saver.restore(self.session, config.save_path)
                print('Restore the model from %s successfully.' % config.save_path)
            except:
                print('Fail to restore the model from', config.save_path)
                self.session.run(tf.global_variables_initializer())

    def train(self):
        cfg = self.config
        writer = tf.summary.FileWriter(cfg.logdir, self.session.graph)

        for epoch in range(cfg.epoches):
            batches = self.samples.num() // (cfg.gpus * cfg.batch_size)
            for batch in range(batches):
                feed_dict = {
                    self.tensors.lr: cfg.lr
                }
                for gpu_index in range(cfg.gpus):
                    x, y = self.samples.next_batch(cfg.batch_size)
                    feed_dict[self.tensors.sub_ts[gpu_index].x] = x
                    feed_dict[self.tensors.sub_ts[gpu_index].y] = y
                _, loss, su = self.session.run(
                    [self.tensors.train_op, self.tensors.loss, self.tensors.summary_op], feed_dict)
                writer.add_summary(su, epoch * batches + batch)
                print('%d/%d: loss=%.8f' % (batch, epoch, loss), flush=True)
            self.saver.save(self.session, cfg.save_path)
            print('Save the mode into ', cfg.save_path, flush=True)

    def predict(self):
        pass

    def close(self):
        self.session.close()


if __name__ == '__main__':
    config = Config()
    config.from_cmd_line()

    app = App(config)

    app.train()
    app.close()
    print('Finished!')
