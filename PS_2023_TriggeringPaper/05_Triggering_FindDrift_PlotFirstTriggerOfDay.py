import pandas as pd
import matplotlib.pyplot as plot
import pandas as pd
import numpy as np
import scipy.stats as sp
import datetime as datetime
from datetime import datetime

df = pd.read_csv('')

df.listOfDates = pd.to_datetime(df.listOfDates)
df = df.sort_values('listOfDates')
df = df.reset_index(drop=True)
df['days_from_start'] = df.listOfDates - df.listOfDates[0]

listOfDays = []

startFunction = False
# loop through and organize data, throw out samples that vary too much
for index, row in df.iterrows():
    if index == 0:
        continue
    # if the next index value is greater than the last index value, break the loop
    if index + 1 > df.index[-1]:
        break
    if abs(df.listOfDiscrepancies.iloc[index-1]) < 40:
        startFunction = True
    # get the current and next delta T values
    if startFunction:
        value1 = df.listOfDiscrepancies.iloc[index- 1]
        value2 = df.listOfDiscrepancies.iloc[index]
        # if the difference between the two values is greater than ##, replace the larger value with the smaller value
        if abs(value1 - value2) > 30:
            listOfDays = np.append(listOfDays, df.listOfDates.iloc[index-1])
            df.iloc[index] = df.iloc[index-1]

# drop duplicates
df = df.drop_duplicates()

# eliminate large outliers
indexNames = df[df['listOfDiscrepancies'] > 10 ].index
# Delete these row indexes from dataFrame
df.drop(indexNames , inplace=True)

indexNames = df[df['listOfDiscrepancies'] < -120 ].index
# Delete these row indexes from dataFrame
df.drop(indexNames , inplace=True)

indexDates = df[df['listOfDates'] > datetime(2021,8,30) ].index
# Delete these row indexes from dataFrame
df.drop(indexDates , inplace=True)

y=np.array(df.listOfDiscrepancies, dtype=float)
x=np.array(df.days_from_start.dt.days, dtype=float)

slope, intercept, r_value, p_value, std_err = sp.linregress(x,y)
result = sp.linregress(x,y)
print(result)

xf = np.linspace(min(x),max(x),len(x))
xf1 = xf.copy()
xf1 = pd.to_datetime(xf1)
yf = (slope*xf)+intercept

print('slope = ', slope, '\n', 'r = ', r_value, '\n', 'p = ', p_value, '\n', 's = ', std_err)

plot.scatter(df.days_from_start.dt.days, df.listOfDiscrepancies)
plot.grid()
plot.xticks(rotation = 90)
plot.plot(xf, yf, 'r')
plot.plot(slope)
plot.xticks(rotation = 90)
plot.xlabel("Time since first therapy day (days)")
plot.ylabel("Difference from start of session to first stimulation (sec)")
plot.show()