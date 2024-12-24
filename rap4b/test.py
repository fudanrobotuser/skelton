import can
import threading
import time

#先在命令行众配置 can0
# sudo ip link set can0 up type can bitrate 1000000 dbitrate 5000000 restart-ms 1000 sample-point 0.8 dsample-point 0.75 berr-reporting on fd on
# 参考  https://zhuanlan.zhihu.com/p/11384593589


# 发送 CAN 消息的函数（在主线程中运行）
def send_can_message(bus):   

    try:
        # 创建 CAN 消息
        message = can.Message(arbitration_id=0x1, data=[0x02, 0x49, 0x00], is_extended_id=False)
        # 发送消息
        bus.send(message)
        time.sleep(0.3)

        message = can.Message(arbitration_id=0x2, data=[0x02, 0x49, 0x00], is_extended_id=False)
        bus.send(message)
        time.sleep(0.3)

        message = can.Message(arbitration_id=0x3, data=[0x02, 0x49, 0x00], is_extended_id=False)
        bus.send(message)
        time.sleep(0.3)

        message = can.Message(arbitration_id=0x4, data=[0x02, 0x49, 0x00], is_extended_id=False)
        bus.send(message)
        time.sleep(0.3)

        message = can.Message(arbitration_id=0x601, data=[], is_extended_id=False)
        bus.send(message)
        time.sleep(0.3)

        message = can.Message(arbitration_id=0x602, data=[], is_extended_id=False)
        bus.send(message)
        time.sleep(0.3)

        message = can.Message(arbitration_id=0x603, data=[], is_extended_id=False)
        bus.send(message)
        time.sleep(0.3)

        message = can.Message(arbitration_id=0x604, data=[], is_extended_id=False)
        bus.send(message)
        time.sleep(0.3)
        
    except can.CanError:
        print("Message failed to send")

# 接收 CAN 消息的线程函数
def receive_can_message(bus):
    while True:
        # 接收 CAN 消息
        message = bus.recv()  # 阻塞等待消息
        if message:
            print(f"Message received: {message}")

def main():
    # 设置 CAN 接口，假设使用的是 'can0' 接口
    bus = can.interface.Bus(channel='can0', bustype='socketcan', fd=True)
    
    # 创建并启动接收线程
    receive_thread = threading.Thread(target=receive_can_message, args=(bus,))
    receive_thread.daemon = True  # 设置为守护线程，主程序结束时自动退出
    receive_thread.start()

    # 调用发送函数
    send_can_message(bus)  # 在主线程中执行发送操作

if __name__ == "__main__":
    main()
