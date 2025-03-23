function imdb = proj6_part1_setup_data()
% Code for Computer Vision by James Hays

% This path is assumed to contain 'test' and 'train' which each contain 15
% subdirectories. The train folder has 100 samples of each category and the
% test has an arbitrary amount of each category. This is the exact data and
% train/test split used in Project 4.
SceneJPGsPath = 'ECE736_HW3/problem1/scene/data/15SceneData/';

num_train_per_category = 100;
num_test_per_category  = 100; %can be up to 110
total_images = 15*num_train_per_category + 15 * num_test_per_category;

image_size = [64 64]; %downsampling data for speed and because it hurts
% accuracy surprisingly little

imdb.images.data   = zeros(image_size(1), image_size(2), 1, total_images, 'single');
imdb.images.labels = zeros(1, total_images, 'single');
imdb.images.set    = zeros(1, total_images, 'uint8');
image_counter = 1;

categories = {'bedroom', 'coast', 'forest', 'highway', ...
              'industrial', 'insidecity', 'kitchen', ...
              'livingroom', 'mountain', 'office', 'opencountry', ...
              'store', 'street', 'suburb', 'tallbuilding'};
          
sets = {'train', 'test'};

fprintf('Loading %d train and %d test images from each category\n', ...
          num_train_per_category, num_test_per_category)
fprintf('Each image will be resized to %d by %d\n', image_size(1),image_size(2));

%Read each image and resize it to 64x64
for set = 1:length(sets)
    for category = 1:length(categories)
        cur_path = fullfile( vl_rootnn, SceneJPGsPath, sets{set}, categories{category});
        cur_images = dir( fullfile( cur_path,  '*.jpg') );
        
        if(set == 1)
            fprintf('Taking %d out of %d images in %s\n', num_train_per_category, length(cur_images), cur_path);
            cur_images = cur_images(1:num_train_per_category);
        elseif(set == 2)
            fprintf('Taking %d out of %d images in %s\n', num_test_per_category, length(cur_images), cur_path);
            cur_images = cur_images(1:num_test_per_category);
        end

        for i = 1:length(cur_images)

            cur_image = imread(fullfile(cur_path, cur_images(i).name));
            cur_image = single(cur_image);
            if(size(cur_image,3) > 1)
                fprintf('color image found %s\n', fullfile(cur_path, cur_images(i).name));
                cur_image = rgb2gray(cur_image);
            end
            cur_image = imresize(cur_image, image_size);
                       
            % Stack images into a large 64 x 64 x 1 x total_images matrix
            % images.data
            imdb.images.data(:,:,1,image_counter) = cur_image;            
            imdb.images.labels(  1,image_counter) = category;
            imdb.images.set(     1,image_counter) = set; %1 for train, 2 for test (val?)
            
            image_counter = image_counter + 1;
        end
    end
end

% subtract the mean from train image
sum_img = single(zeros(64, 64));
train_cnt = 0;
for i=1:length(imdb.images.data)
    if imdb.images.set(i) == 1
        train_cnt = train_cnt + 1;
        sum_img = sum_img + imdb.images.data(:,:,1,i);
    end
end
imdb.images.train_mean = sum_img / train_cnt;
for i=1:length(imdb.images.data)
    imdb.images.data(:,:,1,i) = ...
        imdb.images.data(:,:,1,i) - imdb.images.train_mean;
end


