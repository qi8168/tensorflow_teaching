


import tensorflow as tf
import numpy as np
import os
import argparse
import cv2
from tensorflow.examples.tutorials.mnist.input_data import read_data_sets


class Config:
    def __init__(self):
        self.batch_size = 20
        self.size = 28
        self.z_size = 2
        self.convs = 2
        self.filters = 16
        self.classes = 10

        self.gpus = self.get_gpus()

        self.name = 'p32'
        self.sample_path = './data/MNIST_data'
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
        self.sub_tensors = []
        with tf.device('/gpu:0'):
            self.lr = tf.placeholder(tf.float32, [], name = 'lr')
            opt = tf.train.AdadeltaOptimizer(self.lr)

        with tf.variable_scope('cgan'):
            for gpu_index in range(config.gpus):
                self.sub_tensors.append(Sub_tensors(gpu_index, config, opt))
                tf.get_variable_scope().reuse_variables()

        with tf.device('/gpu:0'):
            grad1 = self.merge_grads(lambda ts: ts.grad1)
            grad2 = self.merge_grads(lambda ts: ts.grad2)
            grad3 = self.merge_grads(lambda ts: ts.grad3)

            self.train_op1 = opt.apply_gradients(grad1)
            self.train_op2 = opt.apply_gradients(grad2)
            self.train_op3 = opt.apply_gradients(grad3)

            self.loss1 = tf.reduce_mean([ts.loss1 for ts in self.sub_tensors])
            self.loss2 = tf.reduce_mean([ts.loss2 for ts in self.sub_tensors])
            self.loss3 = tf.reduce_mean([ts.loss3 for ts in self.sub_tensors])

            tf.summary.scalar('loss1', self.loss1)
            tf.summary.scalar('loss2', self.loss2)
            tf.summary.scalar('loss3', self.loss3)

            self.summary_op = tf.summary.merge_all()

            self.show_pars()

    def show_pars(self):
        total = 0
        for var in tf.trainable_variables():
            num = self.get_var_num(var.shape)
            total += num
            print(var.name, var.shape, num)

    def get_var_num(self, shape):
        num = 1
        for s in shape:
            num *= s
        return num

    def merge_grads(self, func):
        indices_grads = {}
        grads = {}
        for ts in self.sub_tensors:
            for g, v in func(ts):
                if isinstance(g, tf.IndexedSlices):
                    if v not in indices_grads:
                        indices_grads[v] = []
                    indices_grads[v].append(g)
                else:
                    if v not in grads:
                        grads[v] = []
                    grads[v].append(g)
        result = [(tf.reduce_mean(grads[v], axis = 0),v) for v in grads]
        for v in indices_grads:
            indices = tf.concat([g.indices for g in indices_grads[v]], axis = 0)
            values = tf.concat([g.values for g in indices_grads[v]], axis=0)
            g = tf.IndexedSlices(values, indices)
            result.append((g, v))
        return result



class Sub_tensors:
    def __init__(self, gpu_index, config: Config, opt: tf.train.AdadeltaOptimizer):
        self.config = config
        with tf.device('/gpu:%d' % gpu_index):
            self.x = tf.placeholder(tf.float32, [None, config.size * config.size], 'x')
            x = tf.reshape(self.x, [-1, config.size, config.size, 1])
            self.label = tf.placeholder(tf.int32, [None], 'label')
            label = tf.one_hot(self.label, config.classes)
            self.z = tf.placeholder(tf.float32, [None, config.z_size], 'z')

            with tf.variable_scope('discriminator'):
                p1 = self.discriminator(x, label)

            with tf.variable_scope('geneator'):
                fake = self.geneator(self.z, label)
                self.fake = tf.reshape(fake * 255, [-1, config.size, config.size])

            with tf.variable_scope('discriminator', reuse=True):
                p2 = self.discriminator(fake, label)

            self.loss1 = -tf.reduce_mean(tf.log(p1))
            self.loss2 = -tf.reduce_mean(tf.log(1-p2))
            self.loss3 = -tf.reduce_mean(tf.log(p2))

            dis_vars = [var for var in tf.trainable_variables() if 'discriminator' in var.name]
            gen_vars = [var for var in tf.trainable_variables() if 'geneator' in var.name]

            self.grad1 = opt.compute_gradients(self.loss1, dis_vars)
            self.grad2 = opt.compute_gradients(self.loss2, dis_vars)
            self.grad3 = opt.compute_gradients(self.loss3, gen_vars)

    def geneator(self, z, label):
        config = self.config
        size = config.size // int(2 ** config.convs)
        filters = config.filters * (2 ** config.convs)
        z = tf.layers.dense(z, size*size*filters, name = 'dense1')
        label2 = tf.layers.dense(label, size * size * filters, name = 'label_dense1')
        z += label2
        z = tf.reshape(z, [-1, size, size, filters])
        for i in range(config.convs):
            filters //= 2
            size *= 2
            z = tf.layers.conv2d_transpose(z, filters, 3, 2, 'same', activation=tf.nn.relu, name = 'deconv_%d' % i)

            label2 = tf.layers.dense(label, size * size * filters, name = 'label_dense_%d' % i)
            label2 = tf.reshape(label2, [-1, size, size, filters])
            z += label2
        z = tf.layers.conv2d_transpose(z, 1, 3, 1, 'same', name = 'deconv')
        return z

    def discriminator(self, x, label):
        config = self.config
        filters = config.filters
        size = config.size
        for i in range(config.convs):
            filters *= 2

            x = tf.layers.conv2d(x, filters, 3, 1, 'same', activation = tf.nn.relu, name = 'conv_%d' % i)
            x = tf.layers.max_pooling2d(x, 2, 2)

            size //= 2
            label2 = tf.layers.dense(label, size * size * filters, name = 'label_dense_%d' % i)
            label2 = tf.reshape(label2, [-1, size, size, filters])
            # print(i, x.shape, label2.shape)
            x += label2
        x = tf.layers.flatten(x)
        x = tf.layers.dense(x, 1000, tf.nn.relu, name = 'dense1')
        label2 = tf.layers.dense(label, 1000, name = 'label_dense1')
        x += label2
        x = tf.layers.dense(x, 1, name = 'dense2')
        p = tf.nn.sigmoid(x)
        return p









class App:
    def __init__(self, config: Config):
        self.config = config
        graph = tf.Graph()
        with graph.as_default():
            self.samples = read_data_sets(config.sample_path)
            self.file_writer = tf.summary.FileWriter(logdir=config.logdir, graph=graph)
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
        config = self.config
        batches = self.samples.train.num_examples // (config.batch_size * config.gpus)
        for epoch in range(config.epoches):
            for batch in range(batches):
                feed_dict = {
                    self.tensors.lr: config.lr
                }
                for gpu_index in range(config.gpus):
                    x,label = self.samples.train.next_batch(config.batch_size)
                    z = np.random.normal(size = [config.batch_size, config.z_size])
                    feed_dict[self.tensors.sub_tensors[gpu_index].x] = x
                    feed_dict[self.tensors.sub_tensors[gpu_index].label] = label
                    feed_dict[self.tensors.sub_tensors[gpu_index].z] = z
                _, loss1 = self.session.run([self.tensors.train_op1, self.tensors.loss1], feed_dict)
                _, loss2 = self.session.run([self.tensors.train_op2, self.tensors.loss2], feed_dict)
                _, loss3 = self.session.run([self.tensors.train_op3, self.tensors.loss3], feed_dict)
                su = self.session.run(self.tensors.summary_op, feed_dict)
                self.file_writer.add_summary(su, epoch * batches + batch)
                print('%d/%d, loss1 = %f, loss2 = %f, loss3 = %f' % (epoch, batch, loss1, loss2, loss3))
            self.saver.save(self.session, config.save_path)

    def predict(self, batch_size):
        config = self.config
        z = np.random.normal(size = [batch_size, config.z_size])
        label = [i%config.classes for i in range(batch_size)]
        feed_dict = {
            self.tensors.sub_tensors[0].z: z,
            self.tensors.sub_tensors[0].label:label
        }
        imgs = self.session.run(self.tensors.sub_tensors[0].fake, feed_dict)
        imgs = np.uint8(imgs)
        imgs = np.reshape((imgs, [-1, config.size]))
        cv2.imshow(imgs, 'img')
        cv2.waitKey()



    def close(self):
        self.session.close()


if __name__ == '__main__':
    config = Config()
    config.from_cmd_line()

    # s = Samples(config)
    # img = s.get_sample()
    # cv2.imshow('My pic', np.uint8(img))
    # cv2.waitKey()


    Tensors(config)

    # app = App(config)
    #
    # app.train()
    # app.close()
    print('Finished!')
