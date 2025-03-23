clear
clc

trainImages = load_mnist('../../../data/mnist/train-images-idx3-ubyte', 'images');
trainLabels = load_mnist('../../../data/mnist/train-labels-idx1-ubyte', 'labels');
testImages = load_mnist('../../../data/mnist/t10k-images-idx3-ubyte', 'images');
testLabels = load_mnist('../../../data/mnist/t10k-labels-idx1-ubyte', 'labels');

%% network
trainedNet = load('../../../data/mnist-baseline-simplenn/net-epoch-20.mat');

% delete the softmax layer
trainedNet.net.layers(end) = [];

%to get probabilities
trainedNet.net.layers{end+1} = struct('name', 'prob', 'type', 'softmax');

imgs = testImages;
labels = testLabels;
succ_cnt = 0;
fail_cnt = 0;
for i = 1:size(imgs, 3)
    im = imgs(:,:,i);

    im = single(im);
    % imshow(im)

    res = vl_simplenn(trainedNet.net, im);
    prob = res(end).x(:);
    [max_prob, digit] = max(prob);
    digit = digit - 1;
    if digit == labels(i)
        succ_cnt = succ_cnt + 1;
    else
        fail_cnt = fail_cnt + 1;
    end
end
succ_cnt
fail_cnt
