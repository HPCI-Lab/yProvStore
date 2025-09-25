import BC_connector
import time

timestamp = str(int(time.time()*1000))
result= BC_connector.createResource("PID_"+timestamp,"URI","HASH",timestamp,[])
print("Create",result)

result= BC_connector.readResource("PID_"+timestamp)
print("Read",result)

new_timestamp = str(int(time.time()*1000))
print(new_timestamp)
result= BC_connector.getResourcesByInterval("1756221024155",new_timestamp)
print("GetAll",result)