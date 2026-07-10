# one neuron, no numpy, learning OR gate
import random

w1, w2, b = random.random(), random.random(), random.random()
lr = 0.1
data = [((0,0),0), ((0,1),1), ((1,0),1), ((1,1),1)]

def sigmoid(x):
    return 1 / (1 + 2.71828 ** -x)

for epoch in range(2000):
    for (x1, x2), target in data:
        z = w1*x1 + w2*x2 + b
        pred = sigmoid(z)
        error = pred - target
        # gradient descent update
        w1 -= lr * error * pred * (1-pred) * x1
        w2 -= lr * error * pred * (1-pred) * x2
        b  -= lr * error * pred * (1-pred)

print(w1, w2, b)  # should now predict OR correctly

for (x1, x2), target in data:
    z = w1*x1 + w2*x2 + b
    pred = sigmoid(z)
    answer = 1 if pred >= 0.5 else 0
    print((x1, x2), "pred:", pred, "answer:", answer, "target:", target)