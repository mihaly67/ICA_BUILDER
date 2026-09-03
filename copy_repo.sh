#!/bin/bash
sshpass -e ssh -o StrictHostKeyChecking=no misi@5.189.163.88 "cd /home/misi/LGBM_mlops/Knowledge_Base/External_Repos/DarwinexLabs/tools/dwx_zeromq_connector/ && tar -czf mql-zmq.tar.gz mql-zmq-master/"
sshpass -e scp -o StrictHostKeyChecking=no misi@5.189.163.88:/home/misi/LGBM_mlops/Knowledge_Base/External_Repos/DarwinexLabs/tools/dwx_zeromq_connector/mql-zmq.tar.gz /tmp/mql-zmq.tar.gz
tar -xzf /tmp/mql-zmq.tar.gz -C ./
rm /tmp/mql-zmq.tar.gz
