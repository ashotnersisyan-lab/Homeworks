# -*- coding: utf-8 -*-
"""Ashot_Nersisyan_Regression_HW4.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1uztkHBU_mgrwLZnPvc10IFYNiehTLE3W
"""

# !pip install holidays
# !pip install verstack

# Commented out IPython magic to ensure Python compatibility.
# please install holidays and verstack before running this notebook :)
# from pandas_profiling import ProfileReport
from ydata_profiling import ProfileReport
import verstack
from verstack.stratified_continuous_split import scsplit
import decimal
from datetime import datetime

from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV, KFold
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.preprocessing import StandardScaler, RobustScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn_pandas import DataFrameMapper, gen_features
from sklearn import metrics
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.base import clone
from sklearn.preprocessing import PolynomialFeatures

from sklearn.impute import SimpleImputer
from sklearn.impute import MissingIndicator
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer

from sklearn.preprocessing import StandardScaler, Normalizer, OneHotEncoder, OrdinalEncoder
from sklearn.preprocessing import MinMaxScaler

from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.compose import ColumnTransformer
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_selection import VarianceThreshold

from sklearn.decomposition import PCA, TruncatedSVD, NMF
from sklearn.manifold import TSNE

from sklearn import datasets
from matplotlib import offsetbox

# import umap

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import statsmodels.api as sm

import warnings
import random

random.seed(2023)
seed = 2023

# from IPython.display import set_matplotlib_formats
warnings.filterwarnings('ignore')
# %matplotlib inline

"""# 1. Data Preparation"""

# from google.colab import drive
# drive.mount("/content/drive")

path = "./data/AirQualityUCI.csv"
data = pd.read_csv(path, sep=";")
print(data)

"""## 1.1 Data Preparation and Cleaning

The last 2 column have no data they are the result of the way data was written in the csv.
"""

if "Unnamed: 15" in data.columns:
  data = data.drop(["Unnamed: 15"], axis=1)
if "Unnamed: 16" in data.columns:
  data = data.drop(["Unnamed: 16"], axis=1)

"""We can see that we have NaN only rows at the end of the dataset, I will drop that parts as well."""

data = data.dropna(how="all")

"""Check the types of the columns."""

print(data.shape)
print(data.dtypes.value_counts())
print(data.dtypes)

"""We can see that some of the continuous variables are in obejct format. We need to change their format to float64 to be able to work with them."""

object_to_float_features = list(data.select_dtypes(object).columns)
object_to_float_features.remove("Date")
object_to_float_features.remove("Time")

for column in object_to_float_features:
  data[column] = data[column].str.replace(',', '.', regex=False)
  data[column] = pd.to_numeric(data[column])

print(data.dtypes)

"""As mention in the data documentation all the values -200 are null values, so I will replace them with NaN."""

continious_features = list(data.select_dtypes('number').columns)
print(continious_features)

data[continious_features] = data[continious_features].replace(-200, np.NaN)

print(data.isnull().sum())

"""Seems that 336 rows have no data, except Date and Time. I will delete the rows that have C6H6(GT) NaN as they have no values and check the number of null values again."""

data = data.dropna(subset=["C6H6(GT)"])
print(data.isnull().sum())

"""Reset the indexes after deletion of some rows."""

data.reset_index(inplace=True, drop=True)

total = data.isnull().sum().sort_values(ascending=False)
percent = (data.isnull().sum() / data.isnull().count()).sort_values(ascending=False)
missing_data = pd.concat([total, percent], axis=1, keys=['Total', 'Percent'])
print(missing_data)

"""I will fully drop the column NMHC(GT) as more than 90% of the data is missing. Later will do the split of data to train and test and impute the missing data in the columns CO(GT), NO2(GT) and NOx(GT). I will use multiple imputation as more than 15% of the data is missing in those columns."""

if "NMHC(GT)" in data.columns:
  data = data.drop(["NMHC(GT)"], axis=1)

"""Turn date columns to cyclic sine function using only the day of the year data, it will represent the time of the year, probbably may capture weather changes. Also from the same column will extract day of the week which may represent some cycles over the week. Will do the same with time of the day as it may capture some info on the day level cycles."""

# change the "Date" column type from object to datetime
data["Date"] = pd.to_datetime(data["Date"])

def day_of_year(x):
  return x.timetuple().tm_yday
def day_of_week(x):
  k = x.timetuple().tm_yday
  return k%7
def hour_of_day(s):
  return int(s[0:2])

data["DayYear"] = data["Date"].apply(day_of_year)
data["DayWeek"] = data["Date"].apply(day_of_week)
data["Hour"] = data["Time"].apply(hour_of_day)

print(data[["DayYear", "DayWeek", "Hour"]])
data.dtypes

"""Change the int values of the newly added date and time columns to sine which will capchur the cycles and also bring the values to (-1, 1) range."""

def sin_day_year(x):
	return np.sin((x / 365) * 2 * np.pi)
def sin_day_week(x):
	return np.sin((x / 7) * 2 * np.pi)
def sin_hour(x):
	decimal.getcontext().prec = 6
	tmp = decimal.getcontext().create_decimal(1.357e-05)
	return round((np.sin((x / 24) * 2 * np.pi)), 6)

data["day_year_sin"] = data["DayYear"].apply(sin_day_year)
data["day_week_sin"] = data["DayWeek"].apply(sin_day_week)
data["hour_sin"] = data["Hour"].apply(sin_hour)
print(data[["day_year_sin", "day_week_sin", "hour_sin"]])

# if you want to drop date and time columns overall use the "all_to_drop"
optional_to_drop = ["day_sin", "hour_sin"]
cols_to_drop = ["Date", "Time", "DayYear", "DayWeek", "Hour"]
all_to_drop = optional_to_drop + cols_to_drop
for col in cols_to_drop:
  if col in data.columns:
    data = data.drop([col], axis=1)

print(data.dtypes)

"""## 1.2 Separation of Test from the Dataset

I will split the data to training and test. I will consecuently do EDA on the training part of the data to make sure that the test data was not used in the decision making of the choice and construction of the predictive model.
"""

y = data["C6H6(GT)"]
X = data.drop(["C6H6(GT)"], axis=1)

X_train_all, X_test, y_train_all, y_test = scsplit(X, y, stratify = y, train_size=0.75, test_size=0.25, random_state=seed)

"""Here I used the scsplit to use the stratification by a continuous variable, our target variable in this case."""

print(y_train_all.describe())
print(y_test.describe())

"""We can observe how similar the two distributions are."""

fig, ax = plt.subplots()
sns.distplot(y_train_all, ax=ax)
plt.axvline(y_train_all.mean(), linewidth=1 , color = 'red')
plt.axvline(y_train_all.median(), linewidth=1 , color = 'black')
ax.set_xlim(-10,70)
ax.set_ylim(0,0.09)
plt.title(label="Training dataset distribution",
          fontsize=20,
          color="black")
plt.show();
fig, ax = plt.subplots()
sns.distplot(y_test, ax=ax)
plt.axvline(y_test.mean(), linewidth=1 , color = 'red')
plt.axvline(y_test.median(), linewidth=1 , color = 'black')
ax.set_xlim(-10,70)
ax.set_ylim(0,0.09)
plt.title(label="Test dataset distribution",
          fontsize=20,
          color="black")
plt.show()

"""## 1.3 Delete the Outliers

I will drop the outliers of the training dataset.
"""

# training dataframe with target variable
df_train = pd.concat([X_train_all, y_train_all], axis=1)

"""I wrote a function to help understand the right interval for letting out the outliers. The idea is to modify the multiplier of IQR such that we delete less than specific amout of data from our dataset. You pass to the function the range and the stepsize for the search of the multiplier and give the percentage less than which you are ready to delete the outliers. The function returns the multiplier k that is the lowest for that cause. Then you run the remove_outlier_dataframe function with that k and save the result."""

def remove_outlier(df_in, col_name, k):
    df = df_in.copy()
    q1 = df[col_name].quantile(0.25)
    q3 = df[col_name].quantile(0.75)
    iqr = q3-q1 #Interquartile range
    fence_low  = q1-k*iqr
    fence_high = q3+k*iqr
    # print(fence_low)
    df_null = df[df[col_name].isnull()]
    # print(df_null.shape)
    df = df[df[col_name] > fence_low]
    df = df[df[col_name] < fence_high]
    df = pd.concat([df_null, df])
    return df

def remove_outlier_dataframe(df_in, k):
  Current_df = df_in.copy()
  for col in list(data.select_dtypes('number').columns):
    Current_df = remove_outlier(Current_df, col, k)
  return Current_df

def optimal_range(df_in, a, b, step=0.01, percentage=0.01):
  for i in np.arange(a, b, step):
    df_out = remove_outlier_dataframe(df_in, i)
    # print(1 - (df_out.shape[0]/df_in.shape[0]))
    if 1 - (df_out.shape[0]/df_in.shape[0]) < percentage:
      return i
  return "Not in this range"

opt_k = optimal_range(df_train, 1, 10, step=0.2)
print(opt_k)

print(df_train.shape)
df_train = remove_outlier_dataframe(df_train, opt_k)
print(df_train.shape)

df_train.reset_index(inplace=True, drop=True)

y_train_all = df_train["C6H6(GT)"]
X_train_all = df_train.drop(["C6H6(GT)"], axis=1)

"""# 2. EDA"""

descriptive_stats = df_train.describe(include='all')
print(descriptive_stats)

"""## 2.1 Correlation with Target Variable

Find the features highly correlated with the dependent variable.
"""

corr = df_train.corr()
print(corr["C6H6(GT)"])
condition = np.abs(corr["C6H6(GT)"]) > 0.5
top_corr = corr.loc[condition, condition]
sns.heatmap(top_corr, cmap="coolwarm", vmin=-1, vmax=1, annot=True)

"""I will drop these columns because of very low correlation with the target variable."""

if "RH" in X_train_all.columns:
  X_train_all = X_train_all.drop(["RH"], axis=1)
  X_test = X_test.drop(["RH"], axis=1)
if "day_year_sin" in X_train_all.columns:
  X_train_all = X_train_all.drop(["day_year_sin"], axis=1)
  X_test = X_test.drop(["day_year_sin"], axis=1)
if "day_week_sin" in X_train_all.columns:
  X_train_all = X_train_all.drop(["day_week_sin"], axis=1)
  X_test = X_test.drop(["day_week_sin"], axis=1)

"""## 2.2 Visualization"""

# plots
for col in X_train_all.columns:
  sns.regplot(x=X_train_all[col], y=y_train_all, line_kws={"color":"b","alpha":0.7,"lw":5})
  plt.show()

"""We can see that some of the variables are connected to the target variable linearly. At the same time the realtionships of PT08.S1(CO), PT08.S2(NMHC) and PT08.S3(NOx) can be better described by a polynomial function. Thus we will try polinomial regression as well.

# 3. Regressions
"""

# Evaluation

def evaluate_model(train, val, tr_y, val_y, pipeline):
    pipeline.fit(train, tr_y)
    pred_val = pipeline.predict(val)
    pred_train = pipeline.predict(train)
    mapper = pipeline.named_steps['mapper']

    return pd.DataFrame({
        'train_RMSE': [np.sqrt(mean_squared_error(tr_y, pred_train))], 
        'train_R2': [r2_score(tr_y, pred_train)],
        'val_RMSE': [np.sqrt(mean_squared_error(val_y, pred_val))],
        'val_R2': [r2_score(val_y, pred_val)]
    }), mapper.transformed_names_

"""## 3.1 Basic Linear Regression"""

X_train, X_val, y_train, y_val = train_test_split(X_train_all, y_train_all, 
                                                  random_state=seed, shuffle=True, test_size = 0.2)
X_train_all.reset_index(inplace=True, drop=True)
y_train_all.reset_index(inplace=True, drop=True)

CONTINUOUS = X_train.select_dtypes(include=['float']).columns.tolist()
CYCLICAL = ["hour_sin"] #["day_sin", "hour_sin"]
for cyc in CYCLICAL:
  if cyc in CONTINUOUS:
    CONTINUOUS.remove(cyc)
print(CONTINUOUS, CYCLICAL)

"""Here I will use IterativeImputer for imputation as there was high amount of data missing more than 15% noted earlier. So imputing with the help of the other column will be more accurate."""

imp_mean = IterativeImputer(random_state=seed)
X_train = pd.DataFrame(imp_mean.fit_transform(X_train), columns = X_train.columns)
X_val = pd.DataFrame(imp_mean.transform(X_val), columns = X_train.columns)
X_train_all = pd.DataFrame(imp_mean.fit_transform(X_train_all), columns = X_train_all.columns)
X_test = pd.DataFrame(imp_mean.transform(X_test), columns = X_train_all.columns)

continuous_def = gen_features(
    columns=[[c] for c in CONTINUOUS],
    classes=[
        # {'class': IterativeImputer, 'max_iter': 10},
        {'class': StandardScaler}
    ]
)
cyclical_def = gen_features(
    columns=[[c] for c in CYCLICAL],
    classes=[
        # {'class': SimpleImputer, 'strategy': 'median'},
        {'class': StandardScaler}
    ]
)

features = continuous_def + cyclical_def
mapper = DataFrameMapper(features)
len(features)

X_train_tr = pd.DataFrame(mapper.fit_transform(X_train))
X_val_tr = pd.DataFrame(mapper.transform(X_val))

scaler = StandardScaler()
scaler.fit(np.array(y_train).reshape(-1, 1))
y_train_tr = scaler.transform(np.array(y_train).reshape(-1, 1))
y_val_tr = scaler.transform(np.array(y_val).reshape(-1, 1))

linreg = LinearRegression()
linreg.fit(X_train_tr, y_train_tr)
print(f'\nR2 Score: {linreg.score(X_val_tr, y_val_tr)}')

#cross validation
def rmse(y_gt, Y_pr):
    return np.sqrt(mean_squared_error(y_gt, Y_pr))

print('RMSE val: ')
print(rmse(y_val_tr, linreg.predict(X_val_tr)))
print('-'*30)

rmse_scorer = metrics.make_scorer(rmse)
print('RMSE cross-validation scores:')
CV_score = cross_val_score(linreg, X_train_tr, y_train_tr, cv=5, scoring=rmse_scorer)
print(CV_score)
print('-'*30)

print('RMSE average cross-validation scores:')
print(np.sum(CV_score)/5)
print('-'*30)

#metrics
predictions = linreg.predict(X_val_tr)

mae = metrics.mean_absolute_error(y_val_tr, predictions)
mse = metrics.mean_squared_error(y_val_tr, predictions)
r2 = metrics.r2_score(y_val_tr, predictions)
rmse = np.sqrt(metrics.mean_squared_error(y_val_tr, predictions))

pd.DataFrame.from_dict({'MAE':mae, 'MSE':mse, 'R2':r2, 'RMSE':rmse}, orient='index', columns=['Score'])

"""## 3.2 Polynomial Regression

### Feature Engineering
"""

poly = PolynomialFeatures(2)
X_train_poly = poly.fit_transform(X_train)
X_val_poly = poly.transform(X_val)
X_train_all_poly = poly.fit_transform(X_train_all)
X_test_poly = poly.transform(X_test)
poly_columns = poly.get_feature_names_out(X_train_all.columns)
X_train_poly = pd.DataFrame(X_train_poly, columns=poly_columns)
X_val_poly = pd.DataFrame(X_val_poly, columns=poly_columns)
X_train_all_poly = pd.DataFrame(X_train_all_poly, columns=poly_columns)
X_test_poly = pd.DataFrame(X_test_poly, columns=poly_columns)

CONTINUOUS = poly.get_feature_names_out(X_train.columns)
print(list(CONTINUOUS))

continuous_poly_def = gen_features(
    columns=[[c] for c in CONTINUOUS],
    classes=[
        # {'class': IterativeImputer, 'max_iter': 10},
        {'class': StandardScaler}
    ]
)

features_poly = continuous_poly_def
mapper_poly = DataFrameMapper(features_poly)
len(features_poly)

X_train_poly_tr = pd.DataFrame(mapper_poly.fit_transform(X_train_poly))
X_val_poly_tr = pd.DataFrame(mapper_poly.transform(X_val_poly))

scaler_poly = StandardScaler()
scaler_poly.fit(np.array(y_train).reshape(-1, 1))
y_train_poly_tr = scaler.transform(np.array(y_train).reshape(-1, 1))
y_val_poly_tr = scaler.transform(np.array(y_val).reshape(-1, 1))

polyreg = LinearRegression()
polyreg.fit(X_train_poly_tr, y_train_poly_tr)
print(f'\nR2 Score: {polyreg.score(X_val_poly_tr, y_val_poly_tr)}')

#metrics
predictions = polyreg.predict(X_val_poly_tr)

mae = metrics.mean_absolute_error(y_val_poly_tr, predictions)
mse = metrics.mean_squared_error(y_val_poly_tr, predictions)
r2 = metrics.r2_score(y_val_poly_tr, predictions)
rmse = np.sqrt(metrics.mean_squared_error(y_val_poly_tr, predictions))

pd.DataFrame.from_dict({'MAE':mae, 'MSE':mse, 'R2':r2, 'RMSE':rmse}, orient='index', columns=['Score'])

"""## 3.3 Linear or Polynomial (Optional)

I will try to find the best power of polinomials for the model by a grid search.
"""

cv = KFold(n_splits=5, shuffle=True, random_state=seed)

param_grid = [
    {'mapper__degree': [1, 2]}
  ]
pipeline = Pipeline(steps=[('mapper', PolynomialFeatures()), ('lg', LinearRegression())])
grid_search = GridSearchCV(pipeline, param_grid, cv=cv,
                           scoring=['neg_mean_squared_error', 'r2'],
                           refit='neg_mean_squared_error')

grid_search.fit(pd.DataFrame(mapper.fit_transform(X_train_all)), scaler.transform(np.array(y_train_all).reshape(-1, 1)))

grid_search.best_params_

"""According to the grid search algorithm the optimal regression is the polynomial regression. This is quite natural as we increase the number of feature, so we will have a higher R Squared value. It would be more usefull to use Adjusted R Squared value for this cause, however the LinearRegression() model metrics does not have the Adjusted R Squared value. I will leave this code as well here as it was part of the experimentation.

## 3.4 Regularization and Hyperparameters Tuning

If you want to scale data before trying the elatic net model just uncomment the scaler line in the pipline in the code below.
"""

continuous_poly_def = gen_features(
    columns=[[c] for c in CONTINUOUS],
    classes=[
        # {'class': IterativeImputer, 'max_iter': 10},
        # {'class': StandardScaler}
    ]
)

features_poly = continuous_poly_def
mapper_poly = DataFrameMapper(features_poly)
len(features_poly)

"""I will use regularization on the polynomial feature, it will help filter out the unrelated feature and result in a better model."""

cv = KFold(n_splits=5, shuffle=True, random_state=seed)
pipeline = Pipeline([
    ('mapper', DataFrameMapper(features_poly)),
    ('estimator', ElasticNet(random_state=seed))
])
grid = {
    'estimator__alpha': np.linspace(0, 300, 10),
    'estimator__l1_ratio': np.arange(0, 1.1, 0.1)
}
gs = GridSearchCV(pipeline, grid, 
                  n_jobs=-1, 
                  scoring=['neg_mean_squared_error', 'r2'], 
                  refit='neg_mean_squared_error',
                  cv=cv)

# Commented out IPython magic to ensure Python compatibility.
# %%time
# gs.fit(X_train_poly, y_train)
#
# print(gs.best_params_)
#
# pipeline = clone(pipeline)
# pipeline.set_params(**gs.best_params_);
#
# scores, col = evaluate_model(X_train_poly, X_val_poly, y_train, y_val, pipeline)
# scores

"""If I do scaling before training the elastic net the optimal hyperparameters are both equal to 0. Thus furter I will just use the polynomial linear regression with scaling.

## 3.5 Feature Importance

### Lasso for Linear
"""

def plot_importance(est, colnames, top_n=20):
    importance = pd.DataFrame({
        'abs_weight': np.abs(est.coef_),
        'feature': colnames
    })
    imp20 = importance.sort_values(by='abs_weight', ascending=False)[:top_n]
    sns.barplot(y='feature', x='abs_weight', data=imp20, orient='h');

lasso = Lasso()
pipeline = Pipeline([('mapper', DataFrameMapper(features)), 
                     ('estimator', lasso)])

scores, colnames = evaluate_model(X_train, X_val, y_train, y_val, pipeline)
scores

plot_importance(pipeline.named_steps['estimator'], colnames)

"""We can see that the most correlated feature PT08.S2(NMHC) with the target value comes to play the largest effect in the regression.

### Ridge for Polynomial
"""

ridge = Ridge()
pipeline = Pipeline([('mapper', DataFrameMapper(features_poly)), 
                     ('estimator', ridge)])

scores, colnames = evaluate_model(X_train_poly, X_val_poly, y_train, y_val, pipeline)
scores

plot_importance(pipeline.named_steps['estimator'], colnames)

"""Here we can see that the PT08.S2(NMHC) of power 2 does a better job in the model of explaining the variance in the target variable.

# 4. Results

Try the 2 main models on the test data and compare the results.

## 4.1 Linear Regression Results
"""

X_train_all_tr = pd.DataFrame(mapper.fit_transform(X_train_all))
X_test_tr = pd.DataFrame(mapper.transform(X_test))

scaler = StandardScaler()
scaler.fit(np.array(y_train_all).reshape(-1, 1))
y_train_all_tr = scaler.transform(np.array(y_train_all).reshape(-1, 1))
y_test_tr = scaler.transform(np.array(y_test).reshape(-1, 1))

"""This time we train on the whole training dataset."""

linreg_final = LinearRegression()
linreg_final.fit(X_train_all_tr, y_train_all_tr)
print(f'\nR2 Score: {linreg_final.score(X_test_tr, y_test_tr)}')

#metrics
predictions = linreg_final.predict(X_test_tr)

mae = metrics.mean_absolute_error(y_test_tr, predictions)
mse = metrics.mean_squared_error(y_test_tr, predictions)
r2 = metrics.r2_score(y_test_tr, predictions)
rmse = np.sqrt(metrics.mean_squared_error(y_test_tr, predictions))

pd.DataFrame.from_dict({'MAE':mae, 'MSE':mse, 'R2':r2, 'RMSE':rmse}, orient='index', columns=['Score'])

"""## 4.2 Polynomial Regression Results"""

X_train_all_poly_tr = pd.DataFrame(mapper_poly.fit_transform(X_train_all_poly))
X_test_poly_tr = pd.DataFrame(mapper_poly.transform(X_test_poly))

scaler_poly = StandardScaler()
scaler_poly.fit(np.array(y_train_all).reshape(-1, 1))
y_train_all_poly_tr = scaler.transform(np.array(y_train_all).reshape(-1, 1))
y_test_poly_tr = scaler.transform(np.array(y_test).reshape(-1, 1))

polyreg_final = LinearRegression()
polyreg_final.fit(X_train_all_poly_tr, y_train_all_poly_tr)
print(f'\nR2 Score: {polyreg_final.score(X_test_poly_tr, y_test_poly_tr)}')

#metrics
predictions = polyreg_final.predict(X_test_poly_tr)

mae = metrics.mean_absolute_error(y_test_poly_tr, predictions)
mse = metrics.mean_squared_error(y_test_poly_tr, predictions)
r2 = metrics.r2_score(y_test_poly_tr, predictions)
rmse = np.sqrt(metrics.mean_squared_error(y_test_poly_tr, predictions))

pd.DataFrame.from_dict({'MAE':mae, 'MSE':mse, 'R2':r2, 'RMSE':rmse}, orient='index', columns=['Score'])

"""We got very high R Squared value on the test set as well indicating that we had not overtrained the model on the training dataset.

## 4.3 Error Visualization
"""

#errors visualization
#can be helpful to better understand behavior of model

predictions = linreg_final.predict(X_test_tr)
errors = y_test_tr - predictions
errors_df = pd.DataFrame(errors, columns = ["Errors"]).set_index(pd.RangeIndex(start=1, stop=len(errors)+1, step=1))

sns.kdeplot(data=errors_df, x="Errors", shade=True)
plt.show()

plt.scatter(y_test_tr, predictions);
plt.title('Relationship of true value vs predicted value')
plt.ylabel('Predictions');
plt.xlabel('True value');
plt.show();

#errors visualization
#can be helpful to better understand behavior of model

predictions = polyreg_final.predict(X_test_poly_tr)
errors = y_test_poly_tr - predictions
errors_df = pd.DataFrame(errors, columns = ["Errors"]).set_index(pd.RangeIndex(start=1, stop=len(errors)+1, step=1))

sns.kdeplot(data=errors_df, x="Errors", shade=True)
plt.show()

plt.scatter(y_test_poly_tr, predictions);
plt.title('Relationship of true value vs predicted value')
plt.ylabel('Predictions');
plt.xlabel('True value');
plt.show();

"""We can clearly see that despite errors for both models are normally distributed, errors of the polynomial model are much densly distributed around 0 than those of the linear model(the desity polts have different scales pay attention to the number on x axis, I did not equalize the graph scales as the normal distribution of the errors of the polynomial model would not be visible.)

To sum up, I would choose the polynomial regression over the linear regression as it does better job to explain the variance of the target value, it offers more precision without overfitting.

## 4.4 Factor-Importance Hypothesis Testing
"""

# import statsmodels.api as sm

X_train_lm = sm.add_constant(X_train_all_poly)
lm = sm.OLS(y_train_all, X_train_lm).fit()
print(lm.summary())

"""We can check the P value if higher than 0.05 we can delete those columns as their coeffitients are not significantly different from 0. That will help us to make the model even lighter without loosing precision."""