demoʾ��
1. USBCANFD��������libusbʵ�֣���ȷ�����л�������libusb-1.0�Ŀ⡣
  	�����ubuntu�����������߰�װ���������£�
  	# apt-get install libusb-1.0-0

2. ��libusbcanfd.so����/libĿ¼��
	# sudo cp libusbcanfd.so /lib

3. ����testĿ¼�����л����շ����̣�
	# sudo ./test

4. ����
	# make

5. ������� sudo ./test������ No such file or directory��
	# cd /lib
	# sudo ln -s libusbcanfd.so libusbcanfd.so.1.0.8


����˵����
	test.c 		������Ĭ����������ͨ����������500k+2M��ͨ��0�ᷢ�ͱ��ģ����Խ�����ͨ���Խ��������ῴ�����Ĵ�ӡ��
	testLin.c 	����������linͨ����һ������վ��һ������վ����վ�ʹ�վ����������Ӧ��
	test_uds.c	������ʾUDS����


�豸���Գ������
1���鿴ϵͳ�Ƿ�����ö�ٵ�usb�豸����ӡ���ǵ�VID/PID��USBCANFDΪ3068:0009����
	# lsusb

2���鿴ϵͳ������USB�豸�ڵ㼰�����Ȩ�ޣ�
	# ls /dev/bus/usb/ -lR

3���޸�usb�豸�ķ���Ȩ��ʹ��ͨ�û����Բ���������xxx��Ӧlsusb�����Ϣ�е�bus��ţ�yyy��Ӧdevice��ţ�
	# chmod 666 /dev/bus/usb/xxx/yyy

4�����Ҫ���ø�����ͨ�û�����USBCANFD�豸��Ȩ�ޣ���Ҫ�޸�udev���ã������ļ���/etc/udev/rules.d/50-usbcanfd.rules���������£�
	SUBSYSTEMS=="usb", ATTRS{idVendor}=="3068", ATTRS{idProduct}=="0009", GROUP="users", MODE="0666"

	���¼���udev��������豸����Ӧ����Ȩ�ޣ�
	# udevadm control --reload

5����ȡ��汾��ʾ����
	# ./version.sh ./libusbcanfd.so
	�����
	# 1.0.3

6���̼������������ļ� https://manual.zlg.cn/web/#/316/12495 ��
	# ./upgrade ./usbcanfd_1_200u_upgrade_2.43.bin 0
