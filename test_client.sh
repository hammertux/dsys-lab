#!/bin/bash

NAME=$1
NUM_MSG=$2
MSG_LEN=$3
MSG=""
H_MSG=""


for i in $(eval echo {1..$MSG_LEN}); do 
		MSG+=`echo -n "A"`
done
for i in $(eval echo {1..$NUM_MSG}); do
		H_MSG+="${MSG}"
		if [ $i -eq $NUM_MSG ]; then
				break;
		fi
		H_MSG+=$'\n'
done


python3 run_client.py $NAME <<EOF
"$H_MSG"
EOF







