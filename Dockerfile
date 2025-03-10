FROM osrf/ros:humble-desktop

USER root

# RUN mkdir -p ~/ws/src
WORKDIR /home/ros
COPY ./ ./simple_scream_ros_integration
COPY ./entrypoint.sh /
# COPY ./deps/rds_poc_msgs/ ./rds_poc_msgs/
WORKDIR /home/ros/simple_scream_ros_integration/gstscream/ros2_ws

# install RUST and Gstreamer dependencies
RUN apt-get update \ 
    && curl --proto '=https' --tlsv1.2 https://sh.rustup.rs -sSf | bash -s -- -y

# Add .cargo/bin to PATH
ENV PATH="/root/.cargo/bin:${PATH}"

# Check cargo is visible
RUN cargo --help

RUN apt-get install vim -y \
    && apt-get install python3-gi

RUN apt-get update && apt-get install -y \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgstreamer-plugins-bad1.0-dev \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-tools \
    gstreamer1.0-x \
    gstreamer1.0-alsa \
    gstreamer1.0-gl \
    gstreamer1.0-gtk3 \
    gstreamer1.0-qt5 \
    gstreamer1.0-pulseaudio \
    --no-install-recommends

RUN apt-get install -y \
    ros-${ROS_DISTRO}-librealsense2* \
    ros-${ROS_DISTRO}-realsense2-* \
    && rm -rf /var/lib/apt/lists/* 

WORKDIR /home/ros/simple_scream_ros_integration/gstscream/

RUN rm /home/ros/simple_scream_ros_integration/code/wrapper_lib/CMakeCache.txt

RUN rm -rf ros2_ws/build/ ros2_ws/install/ ros2_ws/log/

RUN ./scripts/build.sh

WORKDIR /home/ros/simple_scream_ros_integration/gstscream/ros2_ws

RUN . /opt/ros/$ROS_DISTRO/setup.sh \
    && colcon build 

RUN echo "export ROS_DOMAIN_ID=2" >> ~/.bashrc
RUN echo ". /opt/ros/humble/setup.bash" >> ~/.bashrc
RUN echo ". /home/ros/simple_scream_ros_integration/gstscream/ros2_ws/install/local_setup.bash" >> ~/.bashrc

ENTRYPOINT [ "/entrypoint.sh" ]

STOPSIGNAL SIGKILL
# CMD "echo $(pwd) && ls -l"

