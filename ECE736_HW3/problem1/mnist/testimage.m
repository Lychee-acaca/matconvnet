clear
clc
im = imread("testimage.png");
im = rgb2gray(im);
im = single(im);
im = imresize(im, [28 28]);
im = 255 - im;

%im = im - mean(im(:));
im(im < 1.0) = 0;
%imshow(im)

%% network
trainedNet = load('../../../data/mnist-baseline-simplenn/net-epoch-20.mat');

% delete the softmax layer
trainedNet.net.layers(end) = [];

%to get probabilities
trainedNet.net.layers{end+1} = struct('name', 'prob', 'type', 'softmax');
res = vl_simplenn(trainedNet.net, im);

prob = res(end).x(:);
[max_prob, digit] = max(prob);

digit = digit - 1
max_prob

