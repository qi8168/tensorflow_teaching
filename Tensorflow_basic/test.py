import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt

def get_data(n = 100):
    x = np.linspace(0,10, n)
    y = x * 2 + 3 + np.random.normal(size=n)
    x.shape = -1, 1
    y.shape = -1, 1
    return x, y

class Config:
    def __init__(self):
        self.epoch = 300
        self.name = 11
        self.lr = 0.01
        self.epoch = 300
        self.logdir = './log/{name}'.format(name=self.name)
        self.save_path = './models/{name}/{name}'.format(name=self.name)

class Tensors:
    def __init__(self, config: Config):
        with tf.device('/gpu:0'):
            with tf.variable_scope('net_work'):
                self.lr = tf.placeholder(tf.float32, [], 'lr')
                self.x = tf.placeholder(tf.float32, [None, 1], 'x')
                self.y = tf.placeholder(tf.float32, [None, 1], 'y')

                w = tf.get_variable('w', [1, 1], tf.float32, initializer=tf.random_normal_initializer)
                b = tf.get_variable('b', [1], tf.float32, initializer=tf.zeros_initializer)
                self.y_pred = tf.matmul(self.x, w) + b

            with tf.variable_scope('loss'):
                self.loss = tf.reduce_mean(tf.square(self.y - self.y_pred))
                tf.summary.scalar('loss', self.loss)

            with tf.variable_scope('optimizer'):
                self.train_op = tf.train.GradientDescentOptimizer(config.lr).minimize(self.loss)
                self.summary_op = tf.summary.merge_all()






class Model:
    def __init__(self, config: Config):
        self.config = config
        graph = tf.Graph()
        with graph.as_default():
            conf = tf.ConfigProto()
            conf.allow_soft_placement = True
            self.session = tf.Session(graph=graph, config=conf)

            self.tensors = Tensors(config)
            self.saver = tf.train.Saver()
            self.file_writer = tf.summary.FileWriter(logdir=config.logdir, graph = graph)
            try:
                self.saver.restore(self.session, self.config.save_path)
                print('the model was restorted successfully!')
            except:
                print('the model does not exist, we have to train a new one!')
                self.train()

    def train(self):
        self.session.run(tf.global_variables_initializer())
        x, y = get_data()
        feed_dict = {self.tensors.x: x,
                     self.tensors.y: y,
                     self.tensors.lr: self.config.lr}
        step = 1
        for e in range(self.config.epoch):
            _, su, lo = self.session.run([self.tensors.train_op,
                              self.tensors.summary_op,
                              self.tensors.loss], feed_dict)
            self.file_writer.add_summary(su, step)
            step += 1
            print('epoch=%d, loss=%f' % (e, lo))
        self.saver.save(self.session, self.config.save_path)

    def predict(self):
        x, y = get_data()
        feed_dict = {self.tensors.x: x}
        y_predict = self.session.run(self.tensors.y_pred, feed_dict)
        plt.plot(x, y, 'r+')
        plt.plot(x, y_predict, 'b-')
        plt.show()

    def close(self):
        self.file_writer.close()
        self.session.close()





if __name__ == '__main__':
    config = Config()
    model = Model(config)
    model.predict()
    model.close()