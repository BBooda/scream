#!/bin/bash
# Session name

SESSION="ros_scream_sender_session"


source scream/gstscream/ros2_ws/install/setup.bash

# Start a new tmux session, detach immediately

tmux new-session -d -s $SESSION
 
# Split the window into two panes (left and right)

tmux split-window -h -t $SESSION
 
# Select the right pane (1) and split it into four vertical panes

tmux select-pane -t $SESSION:0.1

tmux split-window -v -t $SESSION

tmux split-window -v -t $SESSION

tmux split-window -v -t $SESSION

# Balance panes to make them equal
tmux select-layout -t $SESSION tiled


# Attach to the session

tmux attach-session -t $SESSION
