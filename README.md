# esi-event-actions

A simple python script that listens to a messaging queue and runs scripts when
specific events are caught.

## Usage

.. code-block:: bash

  cp esi-event-action-listener.conf.sample esi-event-action-listener.conf
  # update the new conf file
  pip install -r requirements.txt
  python esi-event-action-listener.py
