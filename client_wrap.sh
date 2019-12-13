#/bin/bash

NUM_CLT=$1
NUM_MSG=$2
MSG_LEN=$3
TH_TEST=$4

if [ TH_TEST -eq 0]; then
	for i in `seq 1 $NUM_CLT`; do
			/usr/bin/time -a -o data$i expect exp_client.exp "test$i" "$NUM_MSG" "$MSG_LEN"  "$TH_TEST" &
	done 

else
	for i in `seq 1 $NUM_CLT`; do
			/usr/bin/time -a -o data$i expect exp_client.exp "test$i" "$NUM_MSG" "$MSG_LEN" "$TH_TEST" &
	done
fi

wait
