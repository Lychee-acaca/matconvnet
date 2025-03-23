function output = load_mnist(filename, type)
    if strcmp(type, 'images')
        output = load_mnist_images(filename);
    elseif strcmp(type, 'labels')
        output = load_mnist_labels(filename);
    end
end

function [images, labels] = load_mnist_images(filename)
    fileID = fopen(filename, 'rb');

    magic = fread(fileID, 1, 'int32', 0, 'b');
    numImages = fread(fileID, 1, 'int32', 0, 'b');
    numRows = fread(fileID, 1, 'int32', 0, 'b');
    numCols = fread(fileID, 1, 'int32', 0, 'b');

    images = fread(fileID, numImages * numRows * numCols, 'unsigned char');
    images = reshape(images, numCols, numRows, numImages);
    images = permute(images, [2 1 3]);
    
    fclose(fileID);
end

function labels = load_mnist_labels(filename)
    fileID = fopen(filename, 'rb');
    
    magic = fread(fileID, 1, 'int32', 0, 'b');  % 文件魔数
    numLabels = fread(fileID, 1, 'int32', 0, 'b');  % 标签数量
    
    labels = fread(fileID, numLabels, 'unsigned char');
    
    fclose(fileID);
end
