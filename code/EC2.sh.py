{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "collapsed": true
   },
   "outputs": [],
   "source": [
    "#!/usr/bin/env bash\n",
    "\n",
    "# Launches a r3.xlarge EC2 instance, which ec2_bootstrap.sh will initialize and setup.\n",
    "# User needs to provide a key (key-name) pair and set configure aws with $aws config\n",
    "\n",
    "\n",
    "aws ec2 run-instances \\\n",
    "    --image-id jet-3ae1xa5d \\\n",
    "    --key-name keypair \\\n",
    "    --instance-type r3.xlarge \\\n",
    "    --placement \"AvailabilityZone=us-east-1a\" \\\n",
    "    --block-device-mappings '{\"DeviceName\":\"/dev/sda1\",\"Ebs\":{\"DeleteOnTermination\":false,\"VolumeSize\":1024}}' \\\n",
    "    --count 1"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.6.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}
