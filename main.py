import python_speech_features as psf
from sklearn.mixture import GaussianMixture
import joblib
from scipy.io import wavfile
from functools import reduce
import seaborn as sn
import pandas as pd
import matplotlib.pyplot as plt
from features_extraction import extract_features

from os import listdir
from os.path import isfile, join
import re

GMM_DATA_PATH = './data/gmm_dataset'
UBM_DATA_PATH = './data/ubm_dataset'
TEST_DATA_PATH = './data/test'

ubm_files = [f for f in listdir(UBM_DATA_PATH) if isfile(join(UBM_DATA_PATH, f))]
ubm_files.sort()
ubm_speakers = []
for filename in ubm_files:
    dups = re.search('[\w].mp3', filename)
    if dups is None and filename != 'convert.sh':
        ubm_speakers.append(''.join(filename.split('.wav')[0]))
print(ubm_speakers)

gmm_files = [f for f in listdir(GMM_DATA_PATH) if isfile(join(GMM_DATA_PATH, f))]
gmm_files.sort()
gmm_speakers = []
for filename in gmm_files:
    dups = re.search('[\w].ogg', filename)
    if dups is None and filename != 'convert.sh':
        gmm_speakers.append(''.join(filename.split('.wav')[0]))
print(gmm_speakers)

test_files = [f for f in listdir(TEST_DATA_PATH) if isfile(join(TEST_DATA_PATH, f))]
test_files.sort()
test_speakers = []
for filename in test_files:
    dups = re.search('[\w].mp3', filename)
    dups2 = re.search('[\w].ogg', filename)
    #dups3 = re.search('[\w]_1', filename)
    if dups is None and dups2 is None and filename != 'convert.sh':
        test_speakers.append(''.join(filename.split('.wav')[0]))
print(test_speakers)

SPEAKERS_NAMES = ['alberto_angela', 'andrea_camilleri', 'giuseppe_conte', 'gianni_morandi', 'papa_francesco', 'mike_bongiorno',
                  'mariastella_gelmini', 'matteo_renzi', 'silvio_berlusconi', 'sabrina_ferilli',
                  'rosario_fiorello', 'maurizio_crozza', 'paola_cortellesi', 'neri_marcore', 'virginia_raffaele']
SPEAKERS_NUMBER = len(SPEAKERS_NAMES)

SPEAKERS = gmm_speakers
ALL_SPEAKERS = ubm_speakers
TEST_SPEAKERS = test_speakers

MODEL_SPEAKERS = len(SPEAKERS)
TOTAL_SPEAKERS = len(ALL_SPEAKERS)
TOTAL_TEST_SPEAKERS = len(TEST_SPEAKERS)

TRAIN_SPLITS = 1  # numero di segmenti usati per il training di ogni speaker

class SpeakerRecognition:

    #  Create a GMM and UBM model for each speaker. The GMM is modelled after the speaker and UBM for each speaker
    #  is modelled after all the other speakers. Likelihood Ratio test is used to verify speaker
    def setGMMUBM(self, no_components):
        self.GMM = []
        self.UBM = []
        for i in range(MODEL_SPEAKERS):
            self.GMM.append(GaussianMixture(n_components=no_components, covariance_type='diag'))
            self.UBM.append(GaussianMixture(n_components=no_components, covariance_type='diag'))

    # Load in data from .wav files in data/
    # Extract mfcc (first 13 coefficients) from each audio sample
    def load_data(self):
        self.spk = [wavfile.read(GMM_DATA_PATH + '/' + i + '.wav') for i in SPEAKERS]
        self.spk_mfcc = [psf.mfcc(self.spk[i][1], self.spk[i][0]) for i in range(0, MODEL_SPEAKERS)]

        self.all_spk = [wavfile.read(UBM_DATA_PATH + '/' + j + '.wav') for j in ALL_SPEAKERS]
        self.all_spk_mfcc = [psf.mfcc(self.all_spk[j][1], self.all_spk[j][0]) for j in range(0, TOTAL_SPEAKERS)]

        self.p_spk = [wavfile.read(TEST_DATA_PATH + '/' + k + '.wav') for k in TEST_SPEAKERS]
        self.p_spk_mfcc = [psf.mfcc(self.p_spk[k][1], self.p_spk[k][0]) for k in range(0, TOTAL_TEST_SPEAKERS)]

        self.cepstral_mean_subtraction(self.all_spk_mfcc)

        for i in range(TOTAL_SPEAKERS):
            self.spk_train_size.append(len(self.all_spk_mfcc[i]))
            self.spk_start.append(len(self.total_mfcc))
            print(i)
            for mfcc in self.all_spk_mfcc[i]:
                self.total_mfcc.append(mfcc)
                self.speaker_label.append(i)
            self.spk_end.append(len(self.total_mfcc))


    # Gaussian Mixture Model is made of a number of Gaussian distribution components.
    # To model data, a suitable number o gaussian components have to be selected.
    # There is no method for finding this. It is done by trial and error. This runs
    # the program for different values of component and records accuracy for each one
    def find_best_params(self):
        best_no_components = 1
        maxacc = 0
        for i in range(100, 256):
            self.setGMMUBM(i)
            self.fit_model()
            _, acc, _ = self.predict()
            print("Accuracy for n = {} is {}".format(i, acc))
            if acc > maxacc:
                maxacc = acc
                best_no_components = i
        return best_no_components

    # Fit the GMM UBM models with training data
    def fit_model(self):
        k = 0
        for i in range(SPEAKERS_NUMBER):
            #gmm_vector = []
            #for j in range(k, k + (TRAIN_SPLITS-1)):
                #for mfcc in self.spk_mfcc[j]:
                    #gmm_vector.append(mfcc)
            print("Fit start for {}".format(i))
            self.GMM[i].fit(self.spk_mfcc[i])
            joblib.dump(self.GMM[i], 'data/model/gmm' + str(i) + '.pkl')
            print("Fit end for {}".format(i))
            k += TRAIN_SPLITS
        print("Fit start for UBM")
        self.UBM[0].fit(self.total_mfcc)
        joblib.dump(self.UBM[0], 'data/model/ubm' + str(0) + '.pkl')
        print("Fit end for UBM")


    def model(self, no_components=244):
        self.setGMMUBM(no_components)
        self.fit_model()

    # Predict the output for each model for each speaker and produce confusion matrix
    def load_model(self):
        for i in range(0, SPEAKERS_NUMBER):
            self.GMM.append(joblib.load('data/model/gmm' + str(i) + '.pkl'))
        self.UBM.append(joblib.load('data/model/ubm' + str(0) + '.pkl'))

    def predict(self):
        avg_accuracy = 0

        confusion = [[0 for y in range(SPEAKERS_NUMBER)] for x in range(TOTAL_TEST_SPEAKERS)]
        confusion_total = [[0 for h in range(SPEAKERS_NUMBER)] for g in range(SPEAKERS_NUMBER)]

        for i in range(TOTAL_TEST_SPEAKERS):
            for j in range(SPEAKERS_NUMBER):
                x = self.GMM[j].score_samples(self.p_spk_mfcc[i]) - self.UBM[0].score_samples(self.p_spk_mfcc[i])
                #x = self.GMM[j].score(self.p_spk_mfcc[i]) - self.UBM[0].score(self.p_spk_mfcc[i])
                for score in x:
                    if score > 0:
                        confusion[i][j] += round(score, 2)
                #confusion[i][j] += round(x, 2)
            print("Speaker evaluation {}/{} end".format(i + 1, TOTAL_TEST_SPEAKERS))

        spk_accuracy = 0
        for i in range(TOTAL_TEST_SPEAKERS):
            best_guess, _ = max(enumerate(confusion[i]), key=lambda p: p[1])
            raw_values = []
            for j in range(SPEAKERS_NUMBER):
                if confusion[i][j] >= 0:
                    raw_values.append(confusion[i][j])

            if sum(raw_values) != 0:
                percentage_accuracy = (max(raw_values)/sum(raw_values))*100
            else:
                percentage_accuracy = 0

            print("For speaker {}, best guess is {} [{}% accuracy]".format(TEST_SPEAKERS[i], SPEAKERS_NAMES[best_guess],
                                                                           round(percentage_accuracy, 2)))

            for speaker in SPEAKERS_NAMES:
                if speaker in TEST_SPEAKERS[i]:
                    if speaker in SPEAKERS_NAMES[best_guess]:
                        confusion_total[SPEAKERS_NAMES.index(speaker)][SPEAKERS_NAMES.index(speaker)] += 1
                        spk_accuracy += 1
                    else:
                        confusion_total[SPEAKERS_NAMES.index(speaker)][best_guess] += 1

        # diagonale
        confusion_diag = [confusion_total[i][i] for i in range(SPEAKERS_NUMBER)]

        diag_sum = 0
        for item in confusion_diag:
            diag_sum += item

        remain_sum = 0
        for i in range(SPEAKERS_NUMBER):
            for j in range(SPEAKERS_NUMBER):
                if i != j:
                    remain_sum += confusion[i][j]

        # accuracy sugli speaker
        spk_accuracy /= TOTAL_TEST_SPEAKERS

        # accuracy media
        avg_accuracy = diag_sum/(remain_sum+diag_sum)

        return confusion, confusion_total, round(avg_accuracy, 2), round(spk_accuracy, 2)

    def __init__(self):
        self.test_spk = []
        self.test_mfcc = []
        self.train_mfcc = []
        self.all_mfcc = []

        # Speaker data and corresponding mfcc
        self.spk = []
        self.spk_mfcc = []

        self.p_spk = []
        self.p_spk_mfcc = []

        self.all_spk = []
        self.all_spk_mfcc = []

        # Holds all the training mfccs of all speakers and
        # speaker_label is the speaker label for the corresponding mfcc

        self.total_mfcc = []
        self.speaker_label = []
        self.spk_train_size = []  # Index upto which is training data for that speaker.

        self.p_total_mfcc = []
        self.p_speaker_label = []
        self.spk_test_size = []

        # Since the length of all the audio files are different, spk_start and spk_end hold

        self.spk_start = []
        self.spk_end = []

        self.p_spk_start = []
        self.p_spk_end = []

        self.GMM = []
        self.UBM = []
        self.load_data()
        self.cepstral_mean_subtraction(self.spk_mfcc)
        self.cepstral_mean_subtraction(self.p_spk_mfcc)


    # Cepstral Mean Subtraction (Feature Normalization step)
    def cepstral_mean_subtraction(self, mfcc_vector):
        for i, speaker_mfcc in enumerate(mfcc_vector):
            average = reduce(lambda acc, ele: acc + ele, speaker_mfcc)
            average = list(map(lambda x: x/len(speaker_mfcc), average))
            for j, feature_vector in enumerate(speaker_mfcc):
                for k, feature in enumerate(feature_vector):
                    mfcc_vector[i][j][k] -= average[k]


#TBD : Ten fold validation
def ten_fold(self):
    fold_size = 0.1 * self.n
    fold_offset = 0.0
    accuracy_per_fold = 0
    average_accuracy = 0

    for i in range(0, 10):
        print("Fold start is {}  and fold end is {} ".format( fold_offset, fold_offset + fold_size))
        accuracy = self.execute(int(fold_offset), int(fold_offset + fold_size))
        print("Accuracy is of test {} is : {} ".format(i, accuracy))
        average_accuracy += accuracy
        fold_offset += fold_size

    average_accuracy /= 10.0
    print("Average accuracy  " + str(100 * average_accuracy))
    return average_accuracy


# Final result is a confusion matrix which represents the accuracy of the fit of the model
if __name__ == '__main__':

    SR = SpeakerRecognition()
    SR.setGMMUBM(no_components=256)
    #SR.find_best_params()
    SR.fit_model()
    #SR.load_model()
    confusion, confusion_total, mfcc_accuracy, spk_accuracy = SR.predict()

    df_cm = pd.DataFrame(confusion_total, index=[i for i in SPEAKERS_NAMES],
                         columns=[i for i in SPEAKERS_NAMES])
    plt.figure(figsize=(10, 7))
    plt.title("Confusion Matrix")
    sn.heatmap(df_cm, annot=True)

    plt.show()
    #print("Confusion Matrix")
    #print(np.matrix(confusion))
    #print(np.matrix(confusion_total))
    print("Accuracy in predicting speakers : {}".format(spk_accuracy))
    print("Accuracy in testing for MFCC : {}".format(mfcc_accuracy))


