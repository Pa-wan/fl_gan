import flwr as fl
import tensorflow as tf
from keras.datasets.mnist import load_data
from numpy import expand_dims
from layers import create_model, generator_optimizer, discriminator_optimizer, generator_loss, discriminator_loss, seed

(x_train, y_train), (x_test, y_test) = load_data()
x_train = expand_dims(x_train, axis=-1)
x_train = x_train.astype('float32')
x_train = x_train / 255.0

x_test = expand_dims(x_test, axis=-1)
x_test = x_test.astype('float32')
x_test = x_test / 255.0

model = create_model()
model.compile("adam", "sparse_categorical_crossentropy", metrics=["accuracy"])


class GanClient(fl.client.NumPyClient):
    def get_parameters(self):
        return model.get_weights()

    def fit(self, parameters, config):
        BATCH_SIZE = 256
        noise_dim = 100
        generator = model.layers[0]
        discriminator = model.layers[1]
        for i, images in enumerate(x_train):
            noise = tf.random.normal([BATCH_SIZE, noise_dim])

            with tf.GradientTape() as gen_tape, tf.GradientTape() as disc_tape:
                generated_images = generator(noise, training=True)

                real_output = discriminator(images, training=True)
                fake_output = discriminator(generated_images, training=True)

                gen_loss = generator_loss(fake_output)
                disc_loss = discriminator_loss(real_output, fake_output)

            gradients_of_generator = gen_tape.gradient(gen_loss, generator.trainable_variables)
            gradients_of_discriminator = disc_tape.gradient(disc_loss, discriminator.trainable_variables)

            generator_optimizer.apply_gradients(zip(gradients_of_generator, generator.trainable_variables))
            discriminator_optimizer.apply_gradients(zip(gradients_of_discriminator, discriminator.trainable_variables))
            # summarize loss on this batch
            print('%d d=%.3f, g=%.3f' % (i + 1, disc_loss, gen_loss))
        return generator.get_weights(), len(x_train), {}

    def evaluate(self, parameters, config):
        discriminator = model.layers[1]
        generated_images = model(seed, training=False)
        real_output = discriminator(x_test, training=True)
        fake_output = discriminator(generated_images, training=True)
        loss = discriminator_loss(real_output, fake_output)
        return loss, len(x_test), {}


fl.client.start_numpy_client("[::]:8080", client=GanClient())
