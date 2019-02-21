import tensorflow as tf
import numpy as np
import optparse
import os
import shutil
import time
import random
import sys
import pickle
import glob

from layers import *

from tensorflow.examples.tutorials.mnist import input_data
from scipy.misc import imsave
from scipy.misc import imresize
from PIL import Image
from tqdm import tqdm

## added by Jiarui
import misc
## end added by Jiarui

class Fader():

	def run_parser(self):

		self.parser = optparse.OptionParser()

		self.parser.add_option('--num_iter', type='int', default=1000, dest='num_iter')
		self.parser.add_option('--batch_size', type='int', default=32, dest='batch_size')
		self.parser.add_option('--img_width', type='int', default=256, dest='img_width')
		self.parser.add_option('--img_height', type='int', default=256, dest='img_height')
		self.parser.add_option('--img_depth', type='int', default=3, dest='img_depth')
		self.parser.add_option('--num_attr', type='int', default=244, dest='num_attr')
		self.parser.add_option('--max_epoch', type='int', default=64, dest='max_epoch')
		self.parser.add_option('--num_train_images', type='int', default=150000, dest='num_train_images')
		self.parser.add_option('--num_test_images', type='int', default=50000, dest='num_test_images')
		self.parser.add_option('--test', action="store_true", default=False, dest="test")
		self.parser.add_option('--steps', type='int', default=10, dest='steps')
		self.parser.add_option('--enc_size', type='int', default=256, dest='enc_size')
		self.parser.add_option('--dec_size', type='int', default=256, dest='dec_size')
		self.parser.add_option('--model', type='string', default="draw_attn", dest='model_type')
		# self.parser.add_option('--dataset', type='string', default="celebA", dest='dataset')
		# self.parser.add_option('--dataset_dir', type='string', default="/mnt/fcav/3D-lighting/fadenetwork/dataset", dest='dataset_dir')
		# self.parser.add_option('--test_dataset_dir', type='string', default="/mnt/fcav/3D-lighting/fadenetwork/dataset", dest='test_dataset_dir')
		## added by Jiarui
		self.parser.add_option('--train_images_dir', type='string',
							default="/mnt/fcav/3D-lighting/fadenetwork/dataset/all_rgb",
							dest='train_images_dir')
		self.parser.add_option('--train_attributes_file_dir', type='string',
							default="/mnt/fcav/3D-lighting/fadenetwork/dataset/cornellbox_attribute_list_rgb.txt",
							help="attributes txt file directory",
							dest='train_attributes_file_dir')
		self.parser.add_option('--test_images_dir', type='string',
							default="/mnt/fcav/3D-lighting/fadenetwork/dataset/all_rgb",
							dest='test_images_dir')
		self.parser.add_option('--test_attributes_file_dir', type='string',
							default="/mnt/fcav/3D-lighting/fadenetwork/dataset/cornellbox_attribute_list_rgb.txt",
							help="attributes txt file directory",
							dest='test_attributes_file_dir')
		self.parser.add_option('--output_dir', type='string', default="/mnt/fcav/3D-lighting/fadenetwork/results", dest='output_dir')
		## end added by Jiarui


	def initialize(self):

		self.run_parser()

		opt = self.parser.parse_args()[0]

		self.max_epoch = opt.max_epoch
		self.batch_size = opt.batch_size
		# self.dataset = opt.dataset

		self.img_width = opt.img_width
		self.img_height = opt.img_height
		self.img_depth = opt.img_depth

		self.img_size = self.img_width*self.img_height*self.img_depth
		self.num_attr = opt.num_attr
		self.num_train_images = opt.num_train_images
		self.num_test_images = opt.num_test_images
		self.model = "Fader"
		self.to_test = opt.test
		self.load_checkpoint = False
		self.do_setup = True
		## modified by Jiarui
		# self.dataset_dir = opt.dataset_dir
		self.train_images_dir = opt.train_images_dir
		self.train_attr_file_dir = opt.train_attributes_file_dir
		self.test_images_dir = opt.test_images_dir
		self.test_attr_file_dir = opt.test_attributes_file_dir

		# self.tensorboard_dir = "./output/" + self.model + "/" + self.dataset + "/tensorboard"
		# self.check_dir = "./output/"+ self.model + "/" + self.dataset +"/checkpoints"
		# self.images_dir = "./output/" + self.model + "/" + self.dataset + "/imgs"
		self.result_subdir = self.create_result_subdir(opt.output_dir)
		self.tensorboard_dir = self.result_subdir + "/tensorboard"
		self.check_dir = self.result_subdir + "/checkpoints"
		self.images_dir = self.result_subdir + "/imgs"
		## end modified by Jiarui

	## added by Jiarui
	def create_result_subdir(self, result_dir):

		# Select run ID and create subdir.
		while True:
			run_id = 0
			for fname in glob.glob(os.path.join(result_dir, '*')):
				try:
					fbase = os.path.basename(fname)
					ford = int(fbase[:fbase.find('-')])
					run_id = max(run_id, ford + 1)
				except ValueError:
					pass

			result_subdir = os.path.join(result_dir, '%03d-fader' % run_id)
			try:
				os.makedirs(result_subdir)
				break
			except OSError:
				if os.path.isdir(result_subdir):
					continue
				raise

		print("Saving results to", result_subdir)
		misc.set_output_log_file(os.path.join(result_subdir, 'log.txt'))
		return result_subdir
	## end added by Jiarui


	def normalize_input(self, imgs):
		return imgs/127.5-1.0


	def transform_attr(self, attr):

		temp_shape = len(attr)

		final_attr = np.zeros([temp_shape, 2*self.num_attr])

		for i in range(0, temp_shape):
			for j in range(0, self.num_attr):
				final_attr[i][2*j+attr[i][j]] = 1

		return final_attr


	def load_dataset(self, mode='train'):

		if(mode == "train"):

			self.train_attr = []

			## added by Jiarui
			# imageFolderPath = self.dataset_dir
			# self.imagePath = glob.glob(imageFolderPath+'/*.png')
			imageFolderPath = self.train_images_dir
			self.imagePath = glob.glob(imageFolderPath + '/*.png')

			dictn = []

			# count = 0

			# with open(self.dataset_dir+"/train_attr.txt") as f:
			with open(self.train_attr_file_dir) as f:
				for lines in f:
					temp = lines
					temp = temp.split()
					dictn.append(temp[1:])

			for i in range(self.num_train_images):
				# self.train_attr.append(((np.array(dictn[i]).astype(np.int32)+1)/2).astype(np.int32))
				self.train_attr.append(np.array(dictn[i]).astype(np.int32))
			## end added by Jiarui

			self.train_attr_1h = self.transform_attr(self.train_attr)
			# print(self.train_attr[0:10])

		elif (mode == "test"):

			self.test_attr = []

			## added by Jiarui
			# imageFolderPath = self.test_dataset_dir
			# self.imagePath = glob.glob(imageFolderPath+'/*.png')
			imageFolderPath = self.test_images_dir
			self.imagePath = glob.glob(imageFolderPath + '/*.png')

			dictn = []

			# count = 0

			# with open(self.dataset_dir+"/train_attr.txt") as f:
			with open(self.test_attr_file_dir) as f:
				## end added by Jiarui
				for lines in f:
					temp = lines
					temp = temp.split()
					dictn.append(temp[1:])

			for i in range(self.num_test_images):
				self.test_attr.append(np.array(dictn[i]))

	
	def load_batch(self, batch_num, batch_sz, mode="train"):

		if(mode == "train"):
			temp = []
			for i in range(batch_sz):
				temp.append(self.normalize_input(imresize(np.array(Image.open(self.imagePath[i + batch_sz*(batch_num)]),'f')[:,39:216,:], size=[256,256,3], interp="bilinear")))
			return temp

		elif (mode == "test"):
			temp = []
			for i in range(batch_sz):
				temp.append(self.normalize_input(imresize(np.array(Image.open(self.imagePath[num_train_images + i + batch_sz*(batch_num)]),'f')[:,39:216,:], size=[256,256,3], interp="bilinear")))
			return temp

	
	def encoder(self, input_enc, name="Encoder"):

		with tf.variable_scope(name) as scope:

			o_c1 = general_conv2d(input_enc, 16, name="C16", relufactor=0.2)
			o_c2 = general_conv2d(o_c1, 32, name="C32", relufactor=0.2)
			o_c3 = general_conv2d(o_c2, 64, name="C64", relufactor=0.2)
			o_c4 = general_conv2d(o_c3, 128, name="C128", relufactor=0.2)
			o_c5 = general_conv2d(o_c4, 256, name="C256", relufactor=0.2)
			o_c6 = general_conv2d(o_c5, 512, name="C512_1", relufactor=0.2)
			o_c7 = general_conv2d(o_c6, 512, name="C512_2", relufactor=0.2)


			return o_c7

	def decoder(self, input_dec, attr, name="Decoder"):

		with tf.variable_scope(name) as scope:

			attr_1 = tf.transpose(tf.stack([attr]*4),[1, 0, 2])
			o_d0 = tf.concat([input_dec, tf.reshape(attr_1,[-1, 2, 2, 2*self.num_attr])], 3)
			o_d1 = general_deconv2d(o_d0, 512, name="D512_2")
						
			attr_2 = tf.concat([attr_1]*4,axis=1)
			o_d1 = tf.concat([o_d1, tf.reshape(attr_2,[-1, 4, 4, 2*self.num_attr])], 3)			
			o_d2 = general_deconv2d(o_d1, 256, name="D512_1")
			
			attr_3 = tf.concat([attr_2]*4,axis=1)
			o_d2 = tf.concat([o_d2, tf.reshape(attr_3, [-1, 8, 8, 2*self.num_attr])], 3)
			o_d3 = general_deconv2d(o_d2, 128, name="D256")
			
			attr_4 = tf.concat([attr_3]*4,axis=1)
			o_d3 = tf.concat([o_d3, tf.reshape(attr_4, [-1, 16, 16, 2*self.num_attr])], 3)
			o_d4 = general_deconv2d(o_d3, 64, name="D128")
			
			attr_5 = tf.concat([attr_4]*4,axis=1)
			o_d4 = tf.concat([o_d4, tf.reshape(attr_5, [-1, 32, 32, 2*self.num_attr])], 3)
			o_d5 = general_deconv2d(o_d4, 32, name="D64")
			
			attr_6 = tf.concat([attr_5]*4,axis=1)
			o_d5 = tf.concat([o_d5, tf.reshape(attr_6, [-1, 64, 64, 2*self.num_attr])], 3)
			o_d6 = general_deconv2d(o_d5, 16, name="D32")
			
			attr_7 = tf.concat([attr_6]*4,axis=1)
			o_d6 = tf.concat([o_d6, tf.reshape(attr_7, [-1, 128, 128, 2*self.num_attr])], 3)
			o_d7 = general_deconv2d(o_d6, 3, name="D16")

			o_d7 = tf.nn.tanh(o_d7)

			return o_d7


	def discriminator(self, input_disc, name="Discriminator"):

		with tf.variable_scope(name) as scope:

			o_disc1 = general_conv2d(input_disc, 512, name="C512")
			o_disc1 = tf.layers.dropout(o_disc1, rate=0.3)
			size_disc = o_disc1.get_shape().as_list()
			o_flat = tf.reshape(o_disc1,[self.batch_size, 512])
			o_disc2 = linear1d(o_flat, 512, 512, name="fc1")
			o_disc3 = linear1d(o_disc2, 512, self.num_attr, name="fc2")

			return tf.nn.sigmoid(o_disc3)
			

	def celeb_model_setup(self):

		self.input_imgs = tf.placeholder(tf.float32, [self.batch_size, self.img_height, self.img_width, self.img_depth])
		self.input_attr = tf.placeholder(tf.float32, [self.batch_size, self.num_attr])
		self.input_attr_1h = tf.placeholder(tf.float32, [self.batch_size, 2*self.num_attr])
		self.lmda = tf.placeholder(tf.float32,[1])

		with tf.variable_scope("Model") as scope:

			self.o_enc = self.encoder(self.input_imgs)
			self.o_dec = self.decoder(self.o_enc, self.input_attr_1h)
			self.o_disc = self.discriminator(self.o_enc)

	def model_setup(self):

		with tf.variable_scope("Model") as scope:
			self.celeb_model_setup()

		self.model_vars = tf.trainable_variables()
		for var in self.model_vars: print(var.name, var.get_shape())

		self.do_setup = False

	def generation_loss(self, input_img, output_img, loss_type='mse'):

		if (loss_type == 'mse'):
			return tf.reduce_sum(tf.squared_difference(input_img, output_img), [1, 2, 3])
		elif (loss_type == 'log_diff'):
			epsilon = 1e-8
			return -tf.reduce_sum(input_img*tf.log(output_img + epsilon) + (1 - input_img)*tf.log(epsilon + 1 - output_img),[1, 2, 3])


	def discriminator_loss(self, out_attr, inp_attr):

		epsilon = 1e-8
		return tf.reduce_sum(tf.log(tf.abs(out_attr-inp_attr) + epsilon),1)

	def loss_setup(self):

		self.img_loss = tf.reduce_mean(self.generation_loss(self.input_imgs, self.o_dec))
		self.enc_loss = tf.reduce_mean(self.discriminator_loss(self.o_disc, self.input_attr))
		
		self.disc_loss = -tf.reduce_mean(self.discriminator_loss(self.o_disc, 1-self.input_attr))
		self.enc_dec_loss = self.img_loss - self.lmda*self.enc_loss

		optimizer = tf.train.AdamOptimizer(0.002, beta1=0.5)

		enc_dec_vars = [var for var in self.model_vars if 'coder' in var.name]
		disc_vars = [var for var in self.model_vars if 'Discriminator' in var.name]

		self.enc_dec_loss_optimizer = optimizer.minimize(self.enc_dec_loss, var_list=enc_dec_vars)
		self.disc_loss_optimizer = optimizer.minimize(self.disc_loss, var_list=disc_vars)

		self.img_loss_summ = tf.summary.scalar("img_loss", self.img_loss)
		self.enc_loss_summ = tf.summary.scalar("enc_loss", self.enc_loss)
		self.disc_loss_summ = tf.summary.scalar("disc_loss", self.disc_loss)
	

	def train(self):

		self.model_setup()
		self.loss_setup()
		self.load_dataset()


		init = tf.global_variables_initializer()
		saver = tf.train.Saver()

		if not os.path.exists(self.images_dir+"/train/"):
			os.makedirs(self.images_dir+"/train/")
		if not os.path.exists(self.check_dir):
			os.makedirs(self.check_dir)

		with tf.Session() as sess:

			sess.run(init)
			writer = tf.summary.FileWriter(self.tensorboard_dir)
			writer.add_graph(sess.graph)

			if self.load_checkpoint:
				chkpt_fname = tf.train.latest_checkpoint(self.check_dir)
				saver.restore(sess,chkpt_fname)

			per_epoch_steps = int(self.num_train_images/self.batch_size)

			t = time.time()

			for epoch in range(0, self.max_epoch):
				for itr in range(0, per_epoch_steps):

					temp_lmd = 0.0001*(epoch*per_epoch_steps + itr)/(per_epoch_steps*self.max_epoch)

					imgs = self.load_batch(itr, self.batch_size)
					attrs = self.train_attr[itr*self.batch_size:(itr+1)*(self.batch_size)]
					attrs_1h = self.train_attr_1h[itr*self.batch_size:(itr+1)*(self.batch_size)]

					print("In the iteration", itr, "of epoch", epoch)
					print(time.time() - t)

					_, temp_tot_loss, temp_img_loss, temp_enc_loss, img_loss_str, enc_loss_str = sess.run(
						[self.enc_dec_loss_optimizer, self.enc_dec_loss, self.img_loss, self.enc_loss, self.img_loss_summ, self.enc_loss_summ],
						feed_dict={self.input_imgs:imgs, self.input_attr_1h:attrs_1h, self.input_attr:attrs, self.lmda:[temp_lmd]})


					_, temp_disc_loss, disc_loss_str, temp_o_disc = sess.run(
						[self.disc_loss_optimizer, self.disc_loss, self.disc_loss_summ, self.o_disc],
						feed_dict={self.input_imgs:imgs, self.input_attr_1h:attrs_1h, self.input_attr:attrs, self.lmda:[temp_lmd]})

					writer.add_summary(img_loss_str,epoch*per_epoch_steps + itr)
					writer.add_summary(enc_loss_str,epoch*per_epoch_steps + itr)
					writer.add_summary(disc_loss_str,epoch*per_epoch_steps + itr)

					print(temp_tot_loss, temp_img_loss, temp_enc_loss, temp_disc_loss)

				saver.save(sess,os.path.join(self.check_dir,"Fader"),global_step=epoch)

	def test(self):

		self.model_setup()
		self.load_dataset(mode="test")

		if not os.path.exists(self.images_dir+"/test/"):
			os.makedirs(self.images_dir+"/test/")
		if not os.path.exists(self.check_dir):
			os.makedirs(self.check_dir)



		with tf.Session() as sess:

			chkpt_fname = tf.train.latest_checkpoint(self.check_dir)
			saver.restore(sess, chkpt_fname)

			for itr in range(0, int(self.num_test_images/self.batch_size)):

				imgs = self.load_batch(itr, self.batch_size, mode="test")
				attrs = self.test_attr[itr*self.batch_size:(itr+1)*(self.batch_size)]

				temp_output = sess.run([self.o_dec], feed_dict={self.input_imgs:imgs, self.input_attr:attrs})




def main():

	model = Fader()
	model.initialize()

	if(model.to_test):
		model.test()
	else:
		model.train()


if __name__ == "__main__":
	## added by Jiarui
	misc.init_output_logging()
	## end added by Jiarui
	main()