from pathlib import Path

import click
import joblib
import numpy as np
import pandas as pd
from keras.callbacks import EarlyStopping, ModelCheckpoint, TensorBoard
from keras.layers import (Activation, Conv2D, Dense, Dropout, Flatten,
                          MaxPooling2D)
from keras.models import Sequential
from keras.utils import normalize, to_categorical
from sklearn.preprocessing import LabelEncoder

from audiomidi import params


def encode_classes(metadata_paths):

    df = pd.read_json(metadata_paths[0], orient='index')

    for mdp in metadata_paths[1:]:
        df = df.append(pd.read_json(mdp, orient='index'))

    #target = df['instrument_family_str'] + '_' + df['pitch'].astype('str')
    target = df['pitch']

    encoder = LabelEncoder()
    encoder.fit(target)

    return encoder


def prepare_data(data_path, names_path, metadata_path, encoder):

    data = joblib.load(data_path)
    names = joblib.load(names_path)
    metadata = pd.read_json(metadata_path, orient='index')

    df = pd.DataFrame({}, index=names).merge(
        metadata, how='left', left_index=True, right_index=True)
    #target = df['instrument_family_str'] + '_' + df['pitch'].astype('str')
    target = df['pitch']
    target_enc = encoder.transform(target)

    X = data.reshape(data.shape + (1, ))
    y = to_categorical(target_enc, len(encoder.classes_))

    return X, y


def build_model_old(input_shape, num_classes):

    model = Sequential()
    model.add(
        Conv2D(
            64, kernel_size=(3, 3), activation='relu',
            input_shape=input_shape))
    model.add(Conv2D(64, (3, 3), activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.25))
    model.add(Flatten())
    model.add(Dense(128, activation='relu'))
    model.add(Dropout(0.5))
    model.add(Dense(num_classes, activation='softmax'))

    model.compile(
        loss='categorical_crossentropy',
        optimizer='Adadelta',
        metrics=['accuracy'])

    return model


def build_model(input_shape, num_classes):

    model = Sequential()
    model.add(
        Conv2D(
            32, (3, 3),
            padding='same',
            activation='relu',
            input_shape=input_shape))
    model.add(Conv2D(32, (3, 3), activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.25))

    model.add(Conv2D(64, (3, 3), padding='same', activation='relu'))
    model.add(Conv2D(64, (3, 3), activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.25))

    model.add(Conv2D(64, (3, 3), padding='same', activation='relu'))
    model.add(Conv2D(64, (3, 3), activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.25))

    model.add(Flatten())
    model.add(Dense(512, activation='relu'))
    model.add(Dropout(0.5))
    model.add(Dense(num_classes, activation='softmax'))

    model.compile(
        loss='categorical_crossentropy',
        optimizer='rmsprop',
        metrics=['accuracy'])

    return model


def prepare_training():

    weights_file = str(params.weights_dir) + '/' + params.weight_file_pattern
    checkpoint = ModelCheckpoint(weights_file, save_best_only=True)

    earlystopping = EarlyStopping(patience=5)

    log_dir = params.log_dir
    try:
        for log in log_dir.glob('events.out.*'):
            log.unlink()
        click.secho('Previous logs cleared.', fg='bright_yellow')
    except Exception:
        click.secho('Error cleaning previous logs.', fg='bright_red')

    tensorboard = TensorBoard(log_dir=str(log_dir), update_freq=1000)
    click.secho('Log dir: ' + str(log_dir.absolute()), fg='bright_yellow')

    callbacks_list = [checkpoint, earlystopping, tensorboard]

    return callbacks_list


def train_model(model, X_train, y_train, X_valid, y_valid, callbacks):

    fitted_model = model.fit(
        X_train,
        y_train,
        epochs=params.epochs,
        batch_size=params.batch_size,
        callbacks=callbacks,
        validation_data=(X_valid, y_valid),
        verbose=1)

    return fitted_model