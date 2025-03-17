import hazelcast
import threading
import time

def init_hazel_client():
    return hazelcast.HazelcastClient(cluster_name="dev")

def sample_dist_map(hz_client):
    dist_map = hz_client.get_map("distributed-map").blocking()
    for idx in range(1000):
        dist_map.put(idx, f"Value-{idx}")
    print("We placed 1000 items in the distributed map!")

def no_lock_increments(hz_client):
    incr_map = hz_client.get_map("counter-map").blocking()
    incr_map.put_if_absent("shared_key", 0)
    for _ in range(10000):
        val = incr_map.get("shared_key")
        incr_map.put("shared_key", val + 1)
    print("Final result (no locks):", incr_map.get("shared_key"))

def pessimistic_lock_test(hz_client):
    test_map = hz_client.get_map("counter-map").blocking()
    test_map.put_if_absent("shared_key", 0)
    begin_time = time.time()
    for _ in range(10000):
        test_map.lock("shared_key")
        try:
            val = test_map.get("shared_key")
            test_map.put("shared_key", val + 1)
        finally:
            test_map.unlock("shared_key")
    duration = time.time() - begin_time
    print(f"Elapsed (pessimistic lock): {duration:.2f}")
    print("Final result (pessimistic lock):", test_map.get("shared_key"))

def optimistic_lock_test(hz_client):
    opt_map = hz_client.get_map("counter-map").blocking()
    opt_map.put_if_absent("shared_key", 0)
    start_clock = time.time()
    for _ in range(10000):
        while True:
            old_val = opt_map.get("shared_key")

            if opt_map.replace_if_same("shared_key", old_val, old_val + 1):
                break
    end_clock = time.time()
    print(f"Elapsed (optimistic lock): {(end_clock - start_clock):.2f}")
    print("Final result (optimistic lock):", opt_map.get("shared_key"))

def run_bounded_queue_demo(hz_client):
    bounded_q = hz_client.get_queue("bounded-queue").blocking()

    def produce():
        for num in range(1, 101):
            bounded_q.put(num)
            print("Produced:", num)
            time.sleep(0.1)

    def consume(consumer_name):
        while True:
            item = bounded_q.take()
            print(f"{consumer_name} consumed:", item)

    prod_thread = threading.Thread(target=produce)
    cons_thread_1 = threading.Thread(target=consume, args=("Consumer-A",))
    cons_thread_2 = threading.Thread(target=consume, args=("Consumer-B",))

    prod_thread.start()
    cons_thread_1.start()
    cons_thread_2.start()

    prod_thread.join()

def launch():
    client = init_hazel_client()
    # sample_dist_map(client)
    # no_lock_increments(client)
    # pessimistic_lock_test(client)
    # optimistic_lock_test(client)
    run_bounded_queue_demo(client)
    client.shutdown()

if __name__ == "__main__":
    launch()
