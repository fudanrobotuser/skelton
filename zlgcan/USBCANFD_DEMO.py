from ctypes import *
import threading
import time
import datetime

lib = cdll.LoadLibrary("./libusbcanfd.so")

CMD_CAN_FILTER                  = 0x14   # 滤波
CMD_CAN_TTX                     = 0x16   # 定时发送
CMD_CAN_TTX_CTL                 = 0x17   # 使能定时发送
CMD_CAN_TRES                    = 0x18   # CAN终端电阻
ZCAN_CMD_SET_CHNL_RECV_MERGE    = 0x32   # 设置合并接收 0:不合并接收;1:合并接收
ZCAN_CMD_GET_CHNL_RECV_MERGE    = 0x33   # 获取是否开启合并接收 0:不合并接收;1:合并接收
CMD_SET_SN                      = 0x42   # 获取SN号
CMD_GET_SN                      = 0x43   # 设置SN号
CMD_CAN_TX_TIMEOUT              = 0x44   # 发送超时
ZCAN_CMD_GET_SEND_QUEUE_SIZE    = 0x100  # 获取队列大小，uint32_t
ZCAN_CMD_GET_SEND_QUEUE_SPACE   = 0x101  # 获取队列剩余空间, uint32_t
ZCAN_CMD_SET_SEND_QUEUE_CLR     = 0x102  # 清空发送队列,1：清空
ZCAN_CMD_SET_SEND_QUEUE_EN      = 0x103  # 开启发送队列,1：使能

USBCANFD = c_uint32(41)  # 设备类型号
MAX_CHANNELS = 2         # 通道最大数量
g_thd_run = 1            # 线程运行标志
threads = []             # 接收线程

arr_angles = [0] * 8
# can/canfd messgae info
class ZCAN_MSG_INFO(Structure):
    _fields_ = [("txm", c_uint, 4),  # TXTYPE:0 normal,1 once, 2self
                ("fmt", c_uint, 4),  # 0-can2.0 frame,  1-canfd frame
                ("sdf", c_uint, 1),  # 0-data frame, 1-remote frame
                ("sef", c_uint, 1),  # 0-std_frame, 1-ext_frame
                ("err", c_uint, 1),  # error flag
                ("brs", c_uint, 1),  # bit-rate switch ,0-Not speed up ,1-speed up
                ("est", c_uint, 1),  # error state
                ("tx", c_uint, 1),      # received valid, tx frame
                ("echo", c_uint, 1),    # tx valid, echo frame
                ("qsend_100us", c_uint, 1), # queue send delay unit, 1-100us, 0-ms
                ("qsend", c_uint, 1),       # send valid, queue send frame
                ("pad", c_uint, 15)]


# CAN Message Header
class ZCAN_MSG_HDR(Structure):
    _fields_ = [("ts", c_uint32),  # timestamp
                ("id", c_uint32),  # can-id
                ("inf", ZCAN_MSG_INFO),
                ("pad", c_uint16),
                ("chn", c_uint8),  # channel
                ("len", c_uint8)]  # data length

# CAN2.0-frame
class ZCAN_20_MSG(Structure):
    _fields_ = [("hdr", ZCAN_MSG_HDR),
                ("dat", c_ubyte*8)]


# CANFD frame
class ZCAN_FD_MSG(Structure):
    _fields_ = [("hdr", ZCAN_MSG_HDR),
                ("dat", c_ubyte*64)]

# filter_set
class ZCAN_FILTER(Structure):
    _fields_ = [("type", c_uint8),  # 0-std_frame,1-extend_frame
                ("pad", c_uint8*3),  # reserved
                ("sid", c_uint32),  # start_ID
                ("eid", c_uint32)]  # end_ID


class ZCAN_FILTER_TABLE(Structure):
    _fields_ = [("size", c_uint32),  # 滤波数组table实际生效部分的长度
                ("table", ZCAN_FILTER*64)]


class abit_config(Structure):
    _fields_ = [("tseg1", c_uint8),
                ("tseg2", c_uint8),
                ("sjw", c_uint8),
                ("smp", c_uint8),
                ("brp", c_uint16)]


class dbit_config(Structure):
    _fields_ = [("tseg1", c_uint8),
                ("tseg2", c_uint8),
                ("sjw", c_uint8),
                ("smp", c_uint8),
                ("brp", c_uint16)]


class ZCANFD_INIT(Structure):
    _fields_ = [("clk", c_uint32),
                ("mode", c_uint32),
                ("abit", abit_config),
                ("dbit", dbit_config)]

# Terminating resistor
class Resistance(Structure):
    _fields_ = [("res", c_uint8)]

# autosend
class ZCAN_TTX(Structure):
    _fields_ = [("interval", c_uint32),   # 定时发送周期，单位百微秒
                ("repeat", c_uint16),     # 发送次数，0等于循环发
                ("index", c_uint8),       # 定时发送列表的帧索引号，也就是第几条定时发送报文
                ("flags", c_uint8),       # 0-此帧禁用定时发送，1-此帧使能定时发送
                ("msg", ZCAN_FD_MSG)]     # CANFD帧结构体

# autosend list
class ZCAN_TTX_CFG(Structure):
    _fields_ = [("size", c_uint32),       # 实际生效的数组的长度
                ("table", ZCAN_TTX * 8)]  # 最大设置8条

############  uds resoponse #############
class PARAM_DATA(Structure):
    _pack_ = 1
    _fields_ = [("data", c_ubyte*4096)]

class DATA_BUFFER(Structure):
    _pack_ = 1
    _fields_ = [("data", c_ubyte*4096)]

class POSITIVE_DATA(Structure):
    _pack_ = 1
    _fields_ = [("sid", c_ubyte),
                ("data_len", c_uint),
                ]

class NEGATIVE_DATA(Structure):
    _pack_ = 1
    _fields_ = [("neg_code", c_ubyte),
                ("sid", c_ubyte),
                ("error_code", c_ubyte),
                ]

class RESPONSE_DATA(Union):
    _pack_ = 1
    _fields_ = [("positive", POSITIVE_DATA),
                ("negative", NEGATIVE_DATA),
                ("raw", c_byte*8),
                ]

class ZCAN_UDS_RESPONSE(Structure):
    _pack_ = 1
    _fields_ = [
        ("status", c_byte),  # 见ZCAN_UDS_ERROR说明
        ("reserved", c_byte*6),
        ("type", c_byte),  # 0-消极响应,1-积极响应
        ("response", RESPONSE_DATA),
    ]

#######################  uds request #################

class ZCAN_UDS_SESSION_PARAM(Structure):
    _pack_ = 1
    _fields_ = [("p2_timeout", c_uint),
                # 收到消极响应错误码为0x78后的超时时间(ms)。因PC定时器误差，建议设置不小于200ms
                ("enhanced_timeout", c_uint),
                # 接收到非本次请求服务的消极响应时是否需要判定为响应错误
                ("check_any_negative_response", c_ubyte, 1),
                # 抑制响应时是否需要等待消极响应，等待时长为响应超时时间
                ("wait_if_suppress_response", c_ubyte, 1),
                ("flag", c_ubyte, 6),  # 保留
                ("reserved0", c_byte*7)
                ]

class ZCAN_UDS_TRANS_PARAM(Structure):
    _pack_ = 1
    _fields_ = [
        ("version", c_byte),  # 0-2004版本，1-2016版本
        ("max_data_len", c_byte),  # 单帧最大数据长度, can:8, canfd:64
        # 本程序发送流控时用，连续帧之间的最小间隔, 0x00-0x7F(0ms~127ms), 0xF1-0xF9(100us~900us)
        ("local_st_min", c_byte),
        ("block_size", c_byte),  # 流控帧的块大小
        ("fill_byte", c_byte),  # 无效字节的填充数据
        ("ext_frame", c_byte),  # 0:标准帧 1:扩展帧
        # 是否忽略ECU返回流控的STmin，强制使用本程序设置的 remote_st_min
        ("is_modify_ecu_st_min", c_byte),
        # 发送多帧时用, is_ignore_ecu_st_min = 1 时有效, 0x00-0x7F(0ms~127ms), 0xF1-0xF9(100us~900us)
        ("remote_st_min", c_byte),
        ("fc_timeout", c_uint),  # 接收流控超时时间(ms), 如发送首帧后需要等待回应流控帧
        ("fill_mode", c_ubyte),  # 0-FILL_MODE_SHORT,1-FILL_MODE_NONE,2-FILL_MODE_MAX
        ("reserved0", c_byte*3),
    ]

class ZCAN_UDS_REQUEST(Structure):
    _pack_ = 1
    _fields_ = [("req_id", c_uint),         # 请求的事务ID，范围0~65535，本次请求的唯一标识
                ("channel", c_ubyte),       # 设备通道索引
                ("frame_type", c_ubyte),    # 0-can,1-CANFD,2-CANFD加速
                ("reserved0", c_byte*2),
                ("src_addr", c_uint),           # 请求ID
                ("dst_addr", c_uint),           # 响应ID
                ("suppress_response", c_byte),  # 1-抑制响应
                ("sid", c_ubyte),               # 请求服务id
                ("reserved1", c_byte*6),
                ("session_param", ZCAN_UDS_SESSION_PARAM),  # 会话层参数
                ("trans_param", ZCAN_UDS_TRANS_PARAM),      # 传输层参数
                ("data", POINTER(c_ubyte)),                 # 请求参数
                ("data_len", c_uint),                       # 请求参数长度
                ("reserved2", c_uint),
                ]


# 构建 CAN 帧
def construct_can_frame(id, ChIdx, pad):
    can_frame = ZCAN_20_MSG()
    can_frame.hdr.inf.txm = 0  # 0-正常发送, 2--自发自收
    can_frame.hdr.inf.fmt = 0  # 0-CAN
    can_frame.hdr.inf.sdf = 0  # 0-数据帧 1-远程帧
    can_frame.hdr.inf.sef = 0  # 0-标准帧 1- 扩展帧
    #can_frame[i].hdr.inf.echo = 1   # 发送回显

    can_frame.hdr.id = 0x01
    can_frame.hdr.chn = ChIdx
    can_frame.hdr.len = 3

    # 队列发送
    if(pad > 0):
        can_frame.hdr.pad = pad;              # 发送后延迟 pad ms
        can_frame.hdr.inf.qsend = 1;          # 队列发送帧，仅判断首帧
        can_frame.hdr.inf.qsend_100us = 0;    # 队列发送单位，0-ms，1-100us

    for i in range(can_frame.hdr.len):
        can_frame.dat[0] = 0x02
        can_frame.dat[1] = 0x49
        can_frame.dat[2] = 0x00
    return can_frame


#IAP在线更新标志位（必要操作）
def UpdateFlagBit(DevIdx,ChIdx):
    send_num = 4
    # CANFD
    
    for i in range(send_num):
        canfd_frame = ZCAN_20_MSG()
        time.sleep(0.1)
        canfd_frame.hdr.inf.txm = 0  # 0-正常发送
        canfd_frame.hdr.inf.fmt = 1  # 1-CANFD
        canfd_frame.hdr.inf.sdf = 0  # 0-数据帧 CANFD只有数据帧!
        canfd_frame.hdr.inf.sef = 0  # 0-标准帧, 1-扩展帧
        canfd_frame.hdr.inf.brs = 1  # 1-CANFD加速
        canfd_frame.hdr.id = 0x1+i
        canfd_frame.hdr.chn = ChIdx
        canfd_frame.hdr.len = 3
        for i in range(canfd_frame.hdr.len):
            canfd_frame.dat[0] = 0x02
            canfd_frame.dat[1] = 0x49
            canfd_frame.dat[2] = 0x00
        ret = lib.VCI_TransmitFD(USBCANFD, DevIdx, ChIdx, byref(canfd_frame), 1)
        print("TransmitFD num is:%d" % ret)

#GetJointState
def GetJointState(DevIdx,ChIdx):
    send_num = 4
    # CANFD
    for i in range(send_num):
        canfd_frame = ZCAN_20_MSG()
        time.sleep(0.1)
        canfd_frame.hdr.inf.txm = 0  # 0-正常发送
        canfd_frame.hdr.inf.fmt = 1  # 1-CANFD
        canfd_frame.hdr.inf.sdf = 0  # 0-数据帧 CANFD只有数据帧!
        canfd_frame.hdr.inf.sef = 0  # 0-标准帧, 1-扩展帧
        canfd_frame.hdr.inf.brs = 1  # 1-CANFD加速
        canfd_frame.hdr.id = 0x601+i
        canfd_frame.hdr.chn = ChIdx
        canfd_frame.hdr.len = 0
        ret = lib.VCI_TransmitFD(USBCANFD, DevIdx, ChIdx, byref(canfd_frame), 1)
        print("TransmitFD num is:%d" % ret)

def SetPositionMode(DevIdx,ChIdx):
    send_num = 4
    # CANFD
    for i in range(send_num):
        canfd_frame = ZCAN_20_MSG()
        time.sleep(0.1)
        canfd_frame.hdr.inf.txm = 0  # 0-正常发送
        canfd_frame.hdr.inf.fmt = 1  # 1-CANFD
        canfd_frame.hdr.inf.sdf = 0  # 0-数据帧 CANFD只有数据帧!
        canfd_frame.hdr.inf.sef = 0  # 0-标准帧, 1-扩展帧
        canfd_frame.hdr.inf.brs = 1  # 1-CANFD加速
        canfd_frame.hdr.id = 0x1+i
        canfd_frame.hdr.chn = ChIdx
        canfd_frame.hdr.len = 3
        canfd_frame.dat[0] = 0x02
        canfd_frame.dat[1] = 0x30
        canfd_frame.dat[2] = 0x03
        ret = lib.VCI_TransmitFD(USBCANFD, DevIdx, ChIdx, byref(canfd_frame), 1)
        print("TransmitFD num is:%d" % ret) 

def SetPositionValue(DevIdx,ChIdx,Id,Value):
    canfd_frame = ZCAN_20_MSG()
    time.sleep(0.1)
    canfd_frame.hdr.inf.txm = 0  # 0-正常发送
    canfd_frame.hdr.inf.fmt = 1  # 1-CANFD
    canfd_frame.hdr.inf.sdf = 0  # 0-数据帧 CANFD只有数据帧!
    canfd_frame.hdr.inf.sef = 0  # 0-标准帧, 1-扩展帧
    canfd_frame.hdr.inf.brs = 1  # 1-CANFD加速
    canfd_frame.hdr.id = Id
    canfd_frame.hdr.chn = ChIdx
    canfd_frame.hdr.len = 4
    canfd_frame.dat[0] = Value & 0xFF
    canfd_frame.dat[1] = (Value >> 8) & 0xFF
    canfd_frame.dat[2] = (Value >> 16) & 0xFF
    canfd_frame.dat[3] = (Value >> 24) & 0xFF
    print("%02x " % canfd_frame.dat[0], end='')
    print("%02x " % canfd_frame.dat[1], end='')
    print("%02x " % canfd_frame.dat[2], end='')
    print("%02x " % canfd_frame.dat[3], end='')
    ret = lib.VCI_TransmitFD(USBCANFD, DevIdx, ChIdx, byref(canfd_frame), 1)
    print("TransmitFD num is:%d" % ret)         

# 通道初始化，并开启接收线程
def canfd_start(DevType, DevIdx, ChIdx):
    # 波特率结构体，数据根据zcanpro的波特率计算器得出
    canfd_init = ZCANFD_INIT()
    canfd_init.clk = 60000000
    canfd_init.mode = 0

    canfd_init.abit.tseg1 = 2  # 仲裁域
    canfd_init.abit.tseg2 = 0
    canfd_init.abit.sjw = 2
    canfd_init.abit.smp = 80   # smp是采样点，不涉及波特率计算
    canfd_init.abit.brp = 11

    canfd_init.dbit.tseg1 = 1  # 数据域
    canfd_init.dbit.tseg2 = 0
    canfd_init.dbit.sjw = 2
    canfd_init.dbit.smp = 75
    canfd_init.dbit.brp = 2

    # 初始化通道
    ret = lib.VCI_InitCAN(DevType, DevIdx, ChIdx, byref(canfd_init))
    if ret == 0:
        print("InitCAN(%d) fail" % i)
        exit(0)
    else:
        print("InitCAN(%d) success" % i)

    # 使能终端电阻
    Res = c_uint8(1)
    lib.VCI_SetReference(DevType, DevIdx, ChIdx, CMD_CAN_TRES, byref(Res))

    # 启动通道
    ret = lib.VCI_StartCAN(DevType, DevIdx, ChIdx)
    if ret == 0:
        print("StartCAN(%d) fail" % i)
        exit(0)
    else:
        print("StartCAN(%d) success" % i)

    thread = threading.Thread(target=rx_thread, args=(DevType, DevIdx, i,))
    threads.append(thread) # 独立接收线程
    thread.start()
    
def to_int32_signed(value):
    if(value & 0x80000000):
        asdf = bin(value)
        asdf = asdf.replace("0b", "")
        asdf = asdf.replace("0", "A")
        asdf = asdf.replace("1", "0")
        asdf = asdf.replace("A", "1")
        asdf = "0b"+asdf
        return (int(asdf, 2)+1)*(-1)
    else:
        return value 

# 接收线程
def rx_thread(DevType, DevIdx, ChIdx):
    global g_thd_run

    while g_thd_run == 1:       
        count = lib.VCI_GetReceiveNum(DevType, DevIdx, (0x80000000 + ChIdx)) # CANFD 报文数量
        if count > 0:
            canfd_data = (ZCAN_FD_MSG * count)()
            rcount = lib.VCI_ReceiveFD(DevType, DevIdx, ChIdx, byref(canfd_data), count, 100)
            for i in range(rcount):
                print("[%u] chn: %d " %(canfd_data[i].hdr.ts, ChIdx), end='')
                print("TX  " if canfd_data[i].hdr.inf.tx == 1 else "RX  ", end='')
                print("CANFD加速 " if canfd_data[i].hdr.inf.brs == 1 else "CANFD  ", end='')
                print("ID: 0x%x "%(canfd_data[i].hdr.id & 0x1FFFFFFF), end='')
                print("扩展帧  " if canfd_data[i].hdr.inf.sef == 1 else "标准帧  ", end='')

                print("Data: ", end='')
                for j in range(canfd_data[i].hdr.len):
                    print("%02x " % canfd_data[i].dat[j], end='')
                print("")
                if canfd_data[i].hdr.id & 0x1FFFFFFF == 0x701 and ChIdx==0:
                    arr_angles[0] = canfd_data[i].dat[11] * 0x1000000 + canfd_data[i].dat[10] * 0x10000 ++ canfd_data[i].dat[9] * 0x100 + + canfd_data[i].dat[8]
                    arr_angles[0] = to_int32_signed(arr_angles[0])
                if canfd_data[i].hdr.id & 0x1FFFFFFF == 0x702 and ChIdx==0:
                    arr_angles[1] = canfd_data[i].dat[11] * 0x1000000 + canfd_data[i].dat[10] * 0x10000 ++ canfd_data[i].dat[9] * 0x100 + + canfd_data[i].dat[8]
                    arr_angles[1] = to_int32_signed(arr_angles[1])
                if canfd_data[i].hdr.id & 0x1FFFFFFF == 0x703 and ChIdx==0:
                    arr_angles[2] = canfd_data[i].dat[11] * 0x1000000 + canfd_data[i].dat[10] * 0x10000 ++ canfd_data[i].dat[9] * 0x100 + + canfd_data[i].dat[8]
                    arr_angles[2] = to_int32_signed(arr_angles[2])
                if canfd_data[i].hdr.id & 0x1FFFFFFF == 0x704 and ChIdx==0:
                    arr_angles[3] = canfd_data[i].dat[11] * 0x1000000 + canfd_data[i].dat[10] * 0x10000 ++ canfd_data[i].dat[9] * 0x100 + + canfd_data[i].dat[8]
                    arr_angles[3] = to_int32_signed(arr_angles[3])
                if canfd_data[i].hdr.id & 0x1FFFFFFF == 0x701 and ChIdx==1:
                    arr_angles[4] = canfd_data[i].dat[11] * 0x1000000 + canfd_data[i].dat[10] * 0x10000 ++ canfd_data[i].dat[9] * 0x100 + + canfd_data[i].dat[8]
                    arr_angles[4] = to_int32_signed(arr_angles[4])
                if canfd_data[i].hdr.id & 0x1FFFFFFF == 0x702 and ChIdx==1:
                    arr_angles[5] = canfd_data[i].dat[11] * 0x1000000 + canfd_data[i].dat[10] * 0x10000 ++ canfd_data[i].dat[9] * 0x100 + + canfd_data[i].dat[8]
                    arr_angles[5] = to_int32_signed(arr_angles[5])
                if canfd_data[i].hdr.id & 0x1FFFFFFF == 0x703 and ChIdx==1:
                    arr_angles[6] = canfd_data[i].dat[11] * 0x1000000 + canfd_data[i].dat[10] * 0x10000 ++ canfd_data[i].dat[9] * 0x100 + + canfd_data[i].dat[8]
                    arr_angles[6] = to_int32_signed(arr_angles[6])
                if canfd_data[i].hdr.id & 0x1FFFFFFF == 0x704 and ChIdx==1:
                    arr_angles[7] = canfd_data[i].dat[11] * 0x1000000 + canfd_data[i].dat[10] * 0x10000 ++ canfd_data[i].dat[9] * 0x100 + + canfd_data[i].dat[8]
                    arr_angles[7] = to_int32_signed(arr_angles[7])     
                


# 主函数
if __name__ == "__main__":
    DEVICE_INDEX = c_uint32(0)  # 设备索引
    CHANNELS_INDEX = 1         # 测试发送的通道号
    #IsMerge = 0;                # 是否合并接收

    # 打开设备
    ret = lib.VCI_OpenDevice(USBCANFD, DEVICE_INDEX, 0)
    if ret == 0:
        print("Open device fail")
        exit(0)
    else:
        print("Open device success")

    # 打开通道
    for i in range(MAX_CHANNELS):
        canfd_start(USBCANFD, DEVICE_INDEX, i)  # 初始化通道，并且开启接收线程

    #渠道0,1IAP在线更新标志位
    for i in range(MAX_CHANNELS):
        UpdateFlagBit(DEVICE_INDEX,i)
    time.sleep(1)
    #渠道0,1读取角度
    for i in range(MAX_CHANNELS):
        GetJointState(DEVICE_INDEX,i)
    time.sleep(2)
    #打印角度
    print(arr_angles) 
    #渠道0,1更新为位置模式
    for i in range(MAX_CHANNELS):
        SetPositionMode(DEVICE_INDEX,i)  
    time.sleep(1)
    #渠道0,1发送角度
    for i in range(MAX_CHANNELS):
        if(i==0):
            arr_angles[0] += 30000
            SetPositionValue(DEVICE_INDEX,i,0x201,arr_angles[0])
            arr_angles[1] += 30000
            SetPositionValue(DEVICE_INDEX,i,0x202,arr_angles[1])
            arr_angles[2] += 30000
            SetPositionValue(DEVICE_INDEX,i,0x203,arr_angles[2])
            arr_angles[3] += 30000
            SetPositionValue(DEVICE_INDEX,i,0x204,arr_angles[3])     
        else:
            arr_angles[4] += 30000
            SetPositionValue(DEVICE_INDEX,i,0x201,arr_angles[4]) 
            arr_angles[5] += 30000
            SetPositionValue(DEVICE_INDEX,i,0x202,arr_angles[5])
            arr_angles[6] += 30000
            SetPositionValue(DEVICE_INDEX,i,0x203,arr_angles[6])
            arr_angles[7] += 30000
            SetPositionValue(DEVICE_INDEX,i,0x204,arr_angles[7]) 
    # 阻塞等待
    # input()
    g_thd_run = 0

    # 等待所有线程完成
    # for thread in threads:
    #     thread.join()

    for i in range(MAX_CHANNELS):
        ret = lib.VCI_ResetCAN(USBCANFD, DEVICE_INDEX, i)
        if ret == 0:
            print("ResetCAN(%d) fail" % i)
        else:
            print("ResetCAN(%d) success!" % i)

    ret = lib.VCI_CloseDevice(USBCANFD, DEVICE_INDEX)
    if ret == 0:
        print("Closedevice fail!")
    else:
        print("Closedevice success")
    del lib
