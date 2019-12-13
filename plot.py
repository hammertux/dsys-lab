#!/usr/bin/python3

import matplotlib.pyplot as plt
import numpy as np
import csv

stal_rec_x = []
stal_rec_y = []
stal_send_x = []
stal_send_y = []
num_err_x = []
num_err_y = []
ord_err_x = []
ord_err_y = []

_data = np.genfromtxt('./logs/server_errors_31055.csv', delimiter=',')
data = np.delete(_data, (0), axis=0)

for i in data:
    if int(i[2]) == 2:
        num_err_x.append(i[0])
        num_err_y.append((i[1]/10) * 100)
    elif int(i[2]) == 3:
        ord_err_x.append(i[0])
        ord_err_y.append((i[1]/5) * 100)
    elif int(i[2]) == 0:
        stal_rec_x.append(i[0])
        stal_rec_y.append((i[1]/10000000) * 100)
    elif int(i[2]) == 1:
        stal_send_x.append(i[0])
        stal_send_y.append((i[1]/10000000) * 100)

plt.plot(num_err_x, num_err_y, label='num')
plt.plot(ord_err_x, ord_err_y, label='ord')
plt.plot(stal_rec_x, stal_rec_y, label='stal rec')
plt.plot(stal_send_x, stal_send_y, label='stal send')

plt.xlabel('Time in epoch since UTC')
plt.ylabel('% of error')

plt.legend()

plt.show()






