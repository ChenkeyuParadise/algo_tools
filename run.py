from sklearn import (manifold, datasets, decomposition, ensemble, random_projection)
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
import numpy as np
import time
import matplotlib.pyplot as plt
plt.switch_backend('agg')
from matplotlib import offsetbox
import string
## Loading and curating the data
## Function to Scale and visualize the embedding vectors
def plot_embedding(X, title=None):
    x_min, x_max = np.min(X, 0), np.max(X, 0)
    X = (X - x_min) / (x_max - x_min)
    plt.figure()
    ax = plt.subplot(111)
    for i in range(X.shape[0]):
        plt.text(X[i, 0], X[i, 1], str(digits.target[i]),
                 color=plt.cm.Set1(y[i] / 10.),
                 fontdict={'weight': 'bold', 'size': 9})
    if hasattr(offsetbox, 'AnnotationBbox'):
        ## only print thumbnails with matplotlib > 1.0
        shown_images = np.array([[1., 1.]])  # just something big
        for i in range(digits.data.shape[0]):
            dist = np.sum((X[i] - shown_images) ** 2, 1)
            if np.min(dist) < 4e-3:
                ## don't show points that are too close
                continue
            shown_images = np.r_[shown_images, [X[i]]]
            imagebox = offsetbox.AnnotationBbox(
                offsetbox.OffsetImage(digits.images[i], cmap=plt.cm.gray_r),
                X[i])
            ax.add_artist(imagebox)
    plt.xticks([]), plt.yticks([])
    if title is not None:
        plt.title(title)


fin = open("fund_mlr_n_newton_deep_qscore_vector.20180727.template","r")
dic_data = {}
dic_list=[]
target_list=[]
for eachline in fin:
  each_field=eachline.strip().split("")
  template_id = each_field[0]
  vec_str = each_field[1]
  vec_list = [string.atof(ele) for ele in vec_str.split(",")]
  vec_array = np.array(vec_list)
  distance= np.sqrt(np.sum(np.square(vec_array)))
  dic_data.setdefault(template_id, vec_array)
  dic_list.append(vec_array)
  target_list.append(0)
  #print("template_id", template_id)
  #print("distance:", distance)

#emb_output=np.array(dic_list)
file_name="fund_mlr_n_newton_deep_qscore_vector.20180727.nick"
i_cnt=0
with open(file_name,"r") as fin:
  for eachline in fin:
    i_cnt+=1
    if i_cnt % 300 != 0:
      continue
    each_field=eachline.strip().split("")
    template_id = each_field[0]
    vec_str = each_field[1]
    vec_list = [string.atof(ele) for ele in vec_str.split(",")]
    vec_array = np.array(vec_list)
    distance= np.sqrt(np.sum(np.square(vec_array)))
    dic_data.setdefault(template_id, vec_array)
    dic_list.append(vec_array)
    target_list.append(1)
#emb_output=np.concate((emb_output, np.array()), axis=0);
file_name="fund_mlr_n_newton_deep_qscore_vector.20180727.ad"
i_cnt=0
with open(file_name,"r") as fin:
  for eachline in fin:
    i_cnt+=1
    if i_cnt % 300 != 0:
      continue
    each_field=eachline.strip().split("")
    template_id = each_field[0]
    vec_str = each_field[1]
    vec_list = [string.atof(ele) for ele in vec_str.split(",")]
    vec_array = np.array(vec_list)
    distance= np.sqrt(np.sum(np.square(vec_array)))
    dic_data.setdefault(template_id, vec_array)
    dic_list.append(vec_array)
    target_list.append(2)
emb_output=np.array(dic_list)
np_target=np.array(target_list)
print(emb_output.shape)
print(len(target_list))
#exit()
digits = datasets.load_digits(n_class=10)
X = digits.data
y = digits.target
n_samples, n_features = X.shape
n_neighbors = 30
## Computing t-SNE
print(X)
print(X.shape)
#exit()
print("Computing t-SNE embedding")
tsne = manifold.TSNE(n_components=2, init='pca', random_state=0)
t0 = time.time()
X_tsne = tsne.fit_transform(emb_output)
X_pca = PCA().fit_transform(emb_output)
#plot_embedding(X_tsne,
#               "t-SNE embedding of the digits (time %.2fs)" %
#               (time.time() - t0))
plt.figure(figsize=(10, 5))
plt.subplot(121)
plt.scatter(X_tsne[:, 0], X_tsne[:, 1], c=np_target,label="t-SNE")
plt.subplot(122)
plt.scatter(X_pca[:, 0], X_pca[:, 1], c=np_target,label="PCA")
plt.savefig('t-sne.jpg')

