
import time

def linear_interpolation(a, b, total_time, space):
    num = int(total_time / space)
    increment = (b - a) / num

    for i in range(num):
        yield a + i * increment
        time.sleep(space)

    yield b