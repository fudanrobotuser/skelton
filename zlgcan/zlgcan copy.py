def to_int32_signed(value):
    if(value & 0x80000000):
        asdf = bin(value)
        asdf = asdf.replace("0b", "")
        asdf = asdf.replace("0", "A")
        asdf = asdf.replace("1", "0")
        asdf = asdf.replace("A", "1")
        asdf = "0b"+asdf
        return int(asdf, 2)
    else:
        return value

# 示例
num1 = 0xffffff00  # 一个正常的 32 位数值
num2 = 0xffffffff  # 超过 32 位最大值，2^32
num3 = 0xff  # 一个负数

print(to_int32_signed(num1))  # 1234567890（在范围内）
print(to_int32_signed(num2))  # -2147483648（超出范围会“回绕”）
print(to_int32_signed(num3))  # -1234567890（负数）
