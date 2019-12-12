import redis
import time

#make sure to have redis downloaded and to open them on 4 separate ports as below
redisClient_0=redis.StrictRedis(host='localhost', port=6379, db=0) #open revis server 0
redisClient_1=redis.StrictRedis(host='localhost', port=6380, db=1) #open revis server 1
redisClient_2=redis.StrictRedis(host='localhost', port=6381, db=2) #open revis server 2
redisClient_3=redis.StrictRedis(host='localhost', port=6382, db=3) #open revis server 3

if __name__ == "__main__":
	while True:
		try:
			#save all of the various redis servrs every 20 min in order
			redisClient_0.bgsave() #creates background saves
			redisClient_1.bgsave() #can use to later recover lost data if unexpected shutdown
			redisClient_2.bgsave()
			redisClient_3.bgsave()
			time.sleep(1200)
		except:
			print('Error occured')
