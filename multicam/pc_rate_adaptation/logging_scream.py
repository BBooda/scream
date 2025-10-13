# file: scream_line_pub/stdin_pub.py
import sys
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import select

class StdinLinePublisher(Node):
    def __init__(self):
        super().__init__('scream_stdin_publisher')
        self.pub = self.create_publisher(String, 'scream/line', 10)
        self.timer = self.create_timer(0.01, self.poll_stdin)

    def poll_stdin(self):
        # Non-blocking check for input
        rlist, _, _ = select.select([sys.stdin], [], [], 0)
        if sys.stdin in rlist:
            line = sys.stdin.readline()
            if not line:
                self.get_logger().info('EOF on stdin, shutting down.')
                rclpy.shutdown()
                return
            msg = String()
            msg.data = line.strip()
            self.pub.publish(msg)

def main():
    rclpy.init()
    node = StdinLinePublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

