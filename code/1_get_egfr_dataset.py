#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import os
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)
pd.set_option('max_colwidth', 800)
get_ipython().run_line_magic('load_ext', 'autotime')

path = "/Users/metaverse/Desktop/PLS/Data/"
num_values = 18

egfr = pd.read_csv(os.path.join(path, "egfr/EGFR.csv"),sep="|")

# drop nan
egfr = egfr[(egfr.value == egfr.value)]

# get the last num_values recorded values
egfr = egfr[(~egfr.value.str.contains("0,0")) & (egfr.value.str.split(",").str.len() >= num_values)]

# if the patient has more than num_values number of egfr scores, keep the last num_value count of them
egfr.loc[(egfr.value.str.split(",").str.len() > num_values), "value"] =           egfr.value.str.split(",").str[-num_values:].agg(','.join)

# drop rows with non-numeric values
egfr = egfr[~egfr["value"].str.contains(r"[a-zA-Z><\-\*]")]

# drop rows where first or last value is 0
egfr = egfr[~(egfr.value.str.split(",").str[17] == "0") & ~(egfr.value.str.split(",").str[0] == "0")]

# drop all other columns, reset index
egfr = egfr[["patientid","value"]].reset_index(drop=True)


# # add BMI, Systolic, Diastolic, Weight, Cholesterol

# append lab values to egfr dataframe dropping patients who don't have those values
for attr in ["bmi","systolic","diastolic","cholesterol","weight"]:
    df = pd.read_csv(os.path.join(path, "original/NewData/"+attr+".csv"), index_col=0)
    sharedIDs = list(set(egfr.patientid.unique().tolist()) & set(df.patientid.unique().tolist()))
    egfr = egfr[egfr.patientid.isin(sharedIDs)]
    df = df[df.patientid.isin(sharedIDs)]
    df_sorted = df.sort_values(by='recordeddttm')
    df_sorted = df_sorted.drop_duplicates('patientid', keep='last').reset_index(drop=True)
    egfr[attr] = egfr.patientid.map(df_sorted.set_index("patientid")[attr].to_dict())


# # add demographics

demographics = pd.read_csv(os.path.join(path, "egfr/demo.csv"), index_col=0) 
sharedIDs = list(set(egfr.patientid.unique().tolist()) & set(demographics.patientid.unique().tolist()))
egfr = egfr[egfr.patientid.isin(sharedIDs)]
demographics = demographics[demographics.patientid.isin(sharedIDs)]

egfr["sex"] = egfr.patientid.map(demographics.set_index("patientid")["sex"].to_dict())
egfr["sex"].fillna("unknown",inplace=True)

egfr["age"] = egfr.patientid.map(demographics.set_index("patientid")["age"].to_dict())
egfr["age"].fillna(0.0,inplace=True)


# # Interpolate

# get patients that have a zero egfr value
pats_to_interp = egfr[(egfr.value.str.contains(",0,"))].patientid.unique().tolist()
inter = egfr[["patientid","value"]].copy()
inter["value"] = inter["value"].str.split(",")

# explode egfr scores
df1 = inter.value.apply(pd.Series).stack().rename('value')
df2 = df1.to_frame().reset_index(1, drop=True)
inter = df2.join(inter.patientid).reset_index(drop=True)

# replace those values that are . with 0.0
inter.loc[inter.value == ".", "value"] = 0.0

# cast as float
inter["value"] = inter["value"].astype(float)

# interpolate only works on NaNs, set 0.0 to NaN
inter.loc[inter["value"] == 0.0, "value"] = float('NaN')


# append pats that already had a NaN in one of their values to the pats_to_interp list from above
pats_to_interp = inter[inter.value != inter.value].patientid.unique().tolist()+pats_to_interp

# interpolate missing values for only patients with missing valies
for i in pats_to_interp:
    inter[inter.patientid == i] = inter[inter.patientid == i].interpolate(method='polynomial',order=1)


# make a dictionary where key is patientid and value is the interpolated egfr scores
interpo_dict = inter.groupby('patientid')['value'].apply(list).to_dict()

# map the interpolated values back to the egfr dataframe
egfr["value_interped"] = egfr.patientid.map(interpo_dict)


# # One Hot Encode

# split scores into columns
score_cols = ["score_"+str(i) for i in range(1,num_values+1)]
temp = pd.DataFrame(egfr["value_interped"].values.tolist(), columns=score_cols, index=egfr.index)
egfr = egfr.join(temp, how='outer')

# encode gender
egfr = egfr[egfr.sex != "unknown"]
egfr.loc[egfr.sex == "female", "sex"] = 0
egfr.loc[egfr.sex == "male", "sex"] = 1

egfr.drop(["value","value_interped"], axis=1, inplace=True)


egfr[:2]


# # Save

egfr.to_csv(os.path.join(path, "original/NewData/egfr_clean.csv"))


# # Ad hoc, for BI Vis

import pandas as pd
path = "/Users/metaverse/Desktop/grad_school/spring_quarter/prob_stats/homework/project/spring_ps_project/egfr_bi.csv"
egfr_bi = pd.read_csv(path,index_col=0)
egfr_bi[:2]

scores = ["score_"+str(i) for i in range(1,19)]

egfr_bi = egfr_bi[["patientid"]+scores]

egfr_bi[:2]

rename_col = {"score_"+str(i):v+1 for v,i in enumerate(range(1,19))}

egfr_bi.rename(columns=rename_col,inplace=True)

egfr_bi.to_csv(path)




