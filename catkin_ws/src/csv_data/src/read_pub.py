#!/usr/bin/env python

import rospy
import csv
from std_msgs.msg import Int32
from std_msgs.msg import Float64MultiArray

# Global variable to store CSV data
csv_data = []
pub = None  # Global publisher

# Function to read CSV file and store its data in a list
def read_csv_file():
    global csv_data
    try:
        with open('/path/to/your/csv_file.csv', mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                # Convert each row's values to float and store them in the csv_data list
                csv_data.append([float(value) for value in row])
        rospy.loginfo(f"Successfully read {len(csv_data)} rows from the CSV file.")
    except Exception as e:
        rospy.logerr(f"Failed to read CSV file: {e}")

# Callback function for subscriber
def int_callback(msg):
    global csv_data

    # Get the index from the incoming message
    index = msg.data

    # Ensure the index is within the range of rows in CSV
    if 0 <= index < len(csv_data):
        # Get the row of interest
        row = csv_data[index]
        
        # Publish the 8 values as a Float64MultiArray
        output = Float64MultiArray()
        output.data = row
        pub.publish(output)  # Publish the data
        rospy.loginfo(f"Published row {index}: {row}")
    else:
        rospy.logwarn(f"Received invalid index {index}, out of bounds.")

# Main function to initialize ROS node and subscriber
def main():
    global pub
    # Initialize the node
    rospy.init_node('csv_publisher_subscriber', anonymous=True)
    
    # Create the publisher once
    pub = rospy.Publisher('csv_output', Float64MultiArray, queue_size=10)

    # Read the CSV file once at the beginning
    read_csv_file()

    # Subscribe to the integer input topic
    rospy.Subscriber('csv_input', Int32, int_callback)

    # Keep the node running to listen for messages
    rospy.spin()

if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass
