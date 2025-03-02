import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

class CNNNorm(nn.Module):
    """Normalization built for cnns input"""
    def __init__(self, norm_type, n_channels):
        super(CNNNorm, self).__init__()
        if norm_type == 'Group':
            self.norm = nn.GroupNorm(int(n_channels/4), n_channels)
            # If 16 channels, then separate 16 channels into n_groups = n_channels/4 i.e. 16/4 = 4 groups (1 group having 4 channels each)
        elif norm_type == 'Layer':
            self.norm = nn.GroupNorm(1, n_channels)
            # If 16 channels, then separate 16 channels into 1 group & use GroupNorm. This akin to "layer norm"
        elif norm_type == 'Batch':
            self.norm  = nn.BatchNorm2d(n_channels)
        else:
            raise Exception('Illegal normalization type')

    def forward(self, x):
        x = self.norm(x)
        return x

class CNNBlocks(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, padding, dropout_value, norm_type):
        super(CNNBlocks, self).__init__()

        self.cnn     = nn.Conv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=kernel_size, padding=padding, bias=False)
        self.relu    = nn.ReLU()
        self.dropout = nn.Dropout(dropout_value)
        self.norm_type = norm_type
        self.norm = CNNNorm(norm_type, out_channels)

    def forward(self, x):
        x = self.cnn(x)
        x = self.relu(x)
        x = self.norm(x)
        x = self.dropout(x)
        return x


class S6_CNNModel(nn.Module):

    def __init__(self, n_cnn_blocks, n_class, dropout_value, norm_type):
        super(S6_CNNModel, self).__init__()

        self.n_class = n_class
        self.cnn_block0 = nn.Sequential(CNNBlocks(1, 16, (3, 3), 0, dropout_value, norm_type))
        self.cnn_block1 = nn.Sequential(CNNBlocks(16, 16, (3, 3), 0, dropout_value, norm_type))
        self.pool1 = nn.MaxPool2d(2, 2)

        self.cnn_block_2_3_4 = nn.Sequential(*[
            CNNBlocks(16, 16, (3, 3), 0, dropout_value, norm_type)
            for block in range(n_cnn_blocks)
        ])

        self.Gap1 = nn.Sequential(nn.AvgPool2d(kernel_size=6))
        self.fc1 = nn.Conv2d(in_channels=16, out_channels=self.n_class, kernel_size=(1, 1), padding=0, bias=False)

    def forward(self, x):
        x = self.cnn_block0(x)
        x = self.cnn_block1(x)
        x = self.pool1(x)
        x = self.cnn_block_2_3_4(x)
        x = self.Gap1(x)
        x = self.fc1(x)
        x = x.view(-1, self.n_class)
        return F.log_softmax(x, dim=-1)

class S7_CNNModel(nn.Module):

    def __init__(self):
        super(S7_CNNModel, self).__init__()

        # CONVOLUTION BLOCK 1
        self.convblock1A = nn.Sequential(
            nn.Conv2d(in_channels=3, out_channels=64, kernel_size=(3, 3), padding=1, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(64),
        )  # in = 32x32x3 , out = 32x32x32, RF = 3

        self.depthwise1A = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(3, 3), padding=1, bias=False, groups=32),
            nn.ReLU(),
            nn.BatchNorm2d(64),
        )  # in = 32x32x3 * 3x3x3 , out = 32x32x1x32, RF = 5
        self.pointwise1A = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(1, 1), padding=0, bias=False)
        )  # in = 32x32x1X32 , out = 32x32x64, RF = 5

        self.depthwise1B = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(3, 3), padding=1, bias=False, groups=32),
            nn.ReLU(),
            nn.BatchNorm2d(64),
        )  # in = 32x32x64 , out = 32x32x64, RF = 7
        self.pointwise1B = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(1, 1), padding=0, bias=False)
        )  # in = 32x32x1X64 , out = 32x32x64, RF = 7

        self.depthwise1C = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(3, 3), padding=1, bias=False, groups=32),
            nn.ReLU(),
            nn.BatchNorm2d(64),
        )  # in = 32x32x64 , out = 32x32x64, RF = 9
        self.pointwise1C = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=32, kernel_size=(1, 1), padding=0, bias=False)
        )  # in = 32x32x1X64 , out = 32x32x32   , RF = 9

        # TRANSITION BLOCK 1
        self.pool1 = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=0, bias=False, dilation=2),
            nn.ReLU(),
            nn.BatchNorm2d(32),
        )  # in = 32x32x32 , out = 28x28x32  , RF = 13

        # CONVOLUTION BLOCK 2

        self.convblock2A = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=0, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(32),
        )  # in = 24x24x32 , out = 20x20x32, RF = 15

        self.depthwise2A = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=1, bias=False, groups=32),
            nn.ReLU(),
            nn.BatchNorm2d(32),
        )  # in = 28x28x32 * 3x3x3 , out = 28x28x1x32, RF = 17
        self.pointwise2A = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=64, kernel_size=(1, 1), padding=0, bias=False)
        )  # in = 28x28x1X32 , out = 28x28x64    , RF = 17

        self.depthwise2B = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(3, 3), padding=1, bias=False, groups=64),
            nn.ReLU(),
            nn.BatchNorm2d(64),
        )  # in = 28x28x1x64 , out = 28x28x64, RF = 19
        self.pointwise2B = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(1, 1), padding=0, bias=False)
        )  # in = 28x28x64 , out = 28x28x64 , RF = 19

        self.depthwise2C = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(3, 3), padding=1, bias=False, groups=64),
            nn.ReLU(),
            nn.BatchNorm2d(64),
        )  # in = 28x28x1x64 , out = 28x28x64, RF = 21
        self.pointwise2C = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=32, kernel_size=(1, 1), padding=0, bias=False)
        )  # in = 28x28x64 , out = 28x28x32  , RF = 21

        # TRANSITION BLOCK 2
        self.pool2 = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=0, bias=False, dilation=2),
            nn.ReLU(),
            nn.BatchNorm2d(32),
        )  # in = 28x28x32 , out = 24x24x32  , RF = 25

        # CONVOLUTION BLOCK 3
        self.convblock3A = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=0, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(32),
        )  # in = 24x24x32 , out = 20x20x32, RF = 27

        self.depthwise3A = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=1, bias=False, groups=32),
            nn.ReLU(),
            nn.BatchNorm2d(32),
        )  # in = 20x20x32 * 3x3x3 , out = 20x20x1x32, RF = 29
        self.pointwise3A = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=64, kernel_size=(1, 1), padding=0, bias=False)
        )  # in = 20x20x1X32 , out = 20x20x64, RF = 29

        self.depthwise3B = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(3, 3), padding=1, bias=False, groups=32),
            nn.ReLU(),
            nn.BatchNorm2d(64),
        )  # in = 20x20x1x64 , out = 20x20x64, RF = 31
        self.pointwise3B = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(1, 1), padding=0, bias=False)
        )  # in = 20x20x64 , out = 20x20x64 , RF = 31

        self.depthwise3C = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(3, 3), padding=1, bias=False, groups=32),
            nn.ReLU(),
            nn.BatchNorm2d(64),
        )  # in = 20x20x1x64 , out = 20x20x64, RF = 33
        self.pointwise3C = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=32, kernel_size=(1, 1), padding=0, bias=False)
        )  # in = 20x20x64 , out = 20x20x32      , RF = 33

        # TRANSITION BLOCK 3
        self.pool3 = nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), stride=2,
                               padding=1, bias=False)  # in = 20x20x32 , out = 10x10x32, RF = 35

        # CONVOLUTION BLOCK 4
        self.convblock4A = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=0, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(32),
        )  # in = 10X10x32 , out = 8X8x32, RF = 26, RF = 39

        self.convblock4B = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=16, kernel_size=(3, 3), padding=0, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(16),
        )  # in = 8X8x32 , out =6x6x16, RF = 26   , RF = 43

        self.dilated5A = nn.Sequential(
            nn.Conv2d(in_channels=16, out_channels=16, kernel_size=(3, 3), padding=2, bias=False, dilation=2),
            nn.ReLU(),
            nn.BatchNorm2d(16),
        )  # in = 6x6x16 , out = 6x6x16, RF = 7        , RF = 51

        # OUTPUT BLOCK
        self.Gap1 = nn.Sequential(
            nn.AvgPool2d(kernel_size=6)
        )  # in = 6x6x32 , out = 1x1x32, RF = 54	, RF = 61
        self.fc1 = nn.Sequential(
            nn.Conv2d(in_channels=16, out_channels=10, kernel_size=(1, 1), padding=0, bias=False)
        )  # in = 1x1x32 , out = 1x1x10, RF = 54, RF = 61

    def forward(self, x):
        x = self.pointwise1A(self.depthwise1A(self.convblock1A(x)))
        x = self.pointwise1B(self.depthwise1B(x))
        x = self.pointwise1C(self.depthwise1C(x))
        x = self.pool1(x)
        x = self.pointwise2A(self.depthwise2A(self.convblock2A(x)))
        x = self.pointwise2B(self.depthwise2B(x))
        x = self.pointwise2C(self.depthwise2C(x))
        x = self.pool2(x)
        x = self.pointwise3A(self.depthwise3A(self.convblock3A(x)))
        x = self.pointwise3B(self.depthwise3B(x))
        x = self.pointwise3C(self.depthwise3C(x))
        x = self.pool3(x)
        x = self.convblock4B(self.convblock4A(x))
        x = self.dilated5A(x)
        x = self.fc1(self.Gap1(x))
        x = x.view(-1, 10)
        return F.log_softmax(x, dim=-1)


class S7_CNNModel_mixed(nn.Module):

    # Mix of depthwise and depthwise-separable convolutions
    def __init__(self):
        super(S7_CNNModel_mixed, self).__init__()

        # CONVOLUTION BLOCK 0
        self.convblock0A = nn.Sequential(
            nn.Conv2d(in_channels=3, out_channels=32, kernel_size=(3, 3), padding=1, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(32),
        )  # in = 32x32x3 , out = 32x32x32, RF = 3

        # CONVOLUTION BLOCK 1
        self.convblock1A = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=64, kernel_size=(3, 3), padding=1, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(64),
        )  # in = 32x32x3 , out = 32x32x64, RF = 3

        self.depthwise1A = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(3, 3), padding=1, bias=False, groups=32),
            nn.ReLU(),
            nn.BatchNorm2d(64),
        )  # in = 32x32x64 , out = 32x32x64, RF = 7

        self.depthwise1B = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(3, 3), padding=1, bias=False, groups=32),
            nn.ReLU(),
            nn.BatchNorm2d(64),
        )  # in = 32x32x64 , out = 32x32x64, RF = 9

        self.depthwise1C = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(3, 3), padding=1, bias=False, groups=32),
            nn.ReLU(),
            nn.BatchNorm2d(64),
        )  # in = 32x32x64 , out = 32x32x64, RF = 11
        self.pointwise1C = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=32, kernel_size=(1, 1), padding=0, bias=False)
        )  # in = 32x32x1X64 , out = 32x32x32   , RF = 11

        # TRANSITION BLOCK 1
        self.pool1 = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=0, bias=False, dilation=2),
            nn.ReLU(),
            nn.BatchNorm2d(32),
        )  # in = 32x32x32 , out = 28x28x32  , RF = 15

        # CONVOLUTION BLOCK 2

        self.convblock2A = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=0, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(32),
        )  # in = 28x28x32 , out = 26x26x32, RF = 17

        self.depthwise2A = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=1, bias=False, groups=32),
            nn.ReLU(),
            nn.BatchNorm2d(32),
        )  # in = 26x26x32 * 3x3x32 , out = 26x26x1x32, RF = 19
        self.pointwise2A = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=64, kernel_size=(1, 1), padding=0, bias=False)
        )  # in = 26x26x1X32 , out = 26x26x64    , RF = 19

        self.depthwise2B = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(3, 3), padding=1, bias=False, groups=64),
            nn.ReLU(),
            nn.BatchNorm2d(64),
        )  # in = 26x26x64 , out = 26x26x64, RF = 21

        self.depthwise2C = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(3, 3), padding=1, bias=False, groups=64),
            nn.ReLU(),
            nn.BatchNorm2d(64),
        )  # in = 26x26x1x64 , out = 26x26x64, RF = 23
        self.pointwise2C = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=32, kernel_size=(1, 1), padding=0, bias=False)
        )  # in = 26x26x64 , out = 26x26x32  , RF = 23

        # TRANSITION BLOCK 2
        self.pool2 = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=0, bias=False, dilation=2),
            nn.ReLU(),
            nn.BatchNorm2d(32),
        )  # in = 26x26x32 , out = 22x22x32  , RF = 27

        # CONVOLUTION BLOCK 3
        self.convblock3A = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=0, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(32),
        )  # in = 22x22x32 , out = 20x20x32, RF = 29

        self.depthwise3A = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=1, bias=False, groups=32),
            nn.ReLU(),
            nn.BatchNorm2d(32),
        )  # in = 20x20x32 * 3x3x32 , out = 20x20x1x32, RF = 31
        self.pointwise3A = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=64, kernel_size=(1, 1), padding=0, bias=False)
        )  # in = 20x20x1X32 , out = 20x20x64, RF = 31

        self.depthwise3B = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(3, 3), padding=1, bias=False, groups=32),
            nn.ReLU(),
            nn.BatchNorm2d(64),
        )  # in = 20x20x64 , out = 20x20x64, RF = 33

        self.depthwise3C = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=(3, 3), padding=1, bias=False, groups=32),
            nn.ReLU(),
            nn.BatchNorm2d(64),
        )  # in = 20x20x1x64 , out = 20x20x64, RF = 35
        self.pointwise3C = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=32, kernel_size=(1, 1), padding=0, bias=False)
        )  # in = 20x20x64 , out = 20x20x32      , RF = 35

        # TRANSITION BLOCK 3
        self.pool3 = nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), stride=2,
                               padding=1, bias=False)  # in = 20x20x32 , out = 10x10x32, RF = 37

        # CONVOLUTION BLOCK 4
        self.convblock4A = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(3, 3), padding=0, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(32),
        )  # in = 10X10x32 , out = 8X8x32, RF = 41
        self.pointwise4A = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=16, kernel_size=(1, 1), padding=0, bias=False)
        )  # in = 8x8x32 , out = 8x8x16      , RF = 41

        self.convblock4B = nn.Sequential(
            nn.Conv2d(in_channels=16, out_channels=16, kernel_size=(3, 3), padding=0, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(16),
        )  # in = 8X8x16 , out =6x6x16, RF = 45

        self.dilated5A = nn.Sequential(
            nn.Conv2d(in_channels=16, out_channels=16, kernel_size=(3, 3), padding=2, bias=False, dilation=2),
            nn.ReLU(),
            nn.BatchNorm2d(16),
        )  # in = 6x6x16 , out = 6x6x16, RF = 53

        # OUTPUT BLOCK
        self.Gap1 = nn.Sequential(
            nn.AvgPool2d(kernel_size=6)
        )  # in = 6x6x16 , out = 1x1x16, RF = 63
        self.fc1 = nn.Sequential(
            nn.Conv2d(in_channels=16, out_channels=10, kernel_size=(1, 1), padding=0, bias=False)
        )  # in = 1x1x16 , out = 1x1x10, RF = 63

    def forward(self, x):
        x = self.convblock0A(x)
        x = self.depthwise1A(self.convblock1A(x))
        x = self.depthwise1B(x)
        x = self.pointwise1C(self.depthwise1C(x))
        x = self.pool1(x)
        x = self.pointwise2A(self.depthwise2A(self.convblock2A(x)))
        x = self.depthwise2B(x)
        x = self.pointwise2C(self.depthwise2C(x))
        x = self.pool2(x)
        x = self.pointwise3A(self.depthwise3A(self.convblock3A(x)))
        x = self.depthwise3B(x)
        x = self.pointwise3C(self.depthwise3C(x))
        x = self.pool3(x)
        x = self.convblock4B(self.pointwise4A(self.convblock4A(x)))
        x = self.dilated5A(x)
        x = self.fc1(self.Gap1(x))
        x = x.view(-1, 10)
        return F.log_softmax(x, dim=-1)

## S8 - ResNet 18 model for training CIFAR10
class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, in_planes, planes, stride=1):
        super(BasicBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.GroupNorm(1, planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.GroupNorm(1, planes)

        self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != self.expansion * planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_planes, self.expansion * planes, kernel_size=1, stride=stride, bias=False),
                nn.GroupNorm(1, self.expansion * planes)
            )

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        out = F.relu(out)
        return out

class ResNet(nn.Module):
    def __init__(self, block, num_blocks, num_classes=10):
        super(ResNet, self).__init__()
        self.in_planes = 64

        self.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.GroupNorm(1, 64)
        self.layer1 = self._make_layer(block, 64, num_blocks[0], stride=1)
        self.layer2 = self._make_layer(block, 128, num_blocks[1], stride=2)
        self.layer3 = self._make_layer(block, 256, num_blocks[2], stride=2)
        self.layer4 = self._make_layer(block, 512, num_blocks[3], stride=1)  # Modified from stride =2 to stride =1 to stop at 8x8 to train CIFAR-10
        self.Gap1 = nn.AdaptiveAvgPool2d(output_size=(1, 1))
        self.fc = nn.Conv2d(512 * block.expansion, num_classes, kernel_size=1, stride=1, padding=0, bias=False)

    def _make_layer(self, block, planes, num_blocks, stride):
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_planes, planes, stride))
            self.in_planes = planes * block.expansion
        return nn.Sequential(*layers)

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = self.Gap1(out)
        out = self.fc(out)
        out = out.view(out.size(0), -1)
        return F.log_softmax(out, dim=-1)

def ResNet18():
    return ResNet(BasicBlock, [2, 2, 2, 2])

## S9 - Customized ResNet model for training CIFAR10
class BasicBlock_Custom(nn.Module):
    expansion = 1

    def __init__(self, in_planes, planes, make_ind, stride=1):
        super(BasicBlock_Custom, self).__init__()
        self.make_ind = make_ind
        self.conv1 = nn.Conv2d(planes, planes, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)

        self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != self.expansion * planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_planes, self.expansion * planes, kernel_size=3, stride=1, padding=1, bias=False),
                nn.MaxPool2d(2, 2),
                nn.BatchNorm2d(self.expansion * planes)
            )

    def forward(self, x):
        out1 = F.relu(self.shortcut(x))
        if self.make_ind == 'make-block':
            out  = F.relu(self.bn1(self.conv1(out1)))
            out  = F.relu(self.bn2(self.conv2(out)))
            out += out1
        else:
            out  = out1
        return out

class ResNet_Custom(nn.Module):
    def __init__(self, block, num_blocks, num_classes=10):
        super(ResNet_Custom, self).__init__()
        self.in_planes = 64

        self.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.layer1 = self._make_layer(block, 128, num_blocks[0], 'make-block', stride=2)
        self.layer2 = self._make_layer(block, 256, num_blocks[1], 'dont make-block', stride=2)
        self.layer3 = self._make_layer(block, 512, num_blocks[2], 'make-block', stride=2)
        self.maxpool4 = nn.MaxPool2d(4, 4)
        self.fc = nn.Conv2d(512 * block.expansion, num_classes, kernel_size=1, stride=1, padding=0, bias=False)

    def _make_layer(self, block, planes, num_blocks, make_ind, stride):
        strides = [stride-1] + [1] * (num_blocks - 1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_planes, planes, make_ind, stride))
            self.in_planes = planes * block.expansion
        return nn.Sequential(*layers)

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))  # [B, 64, 32, 32]
        out = self.layer1(out)                 # [B, 128, 16, 16]
        out = self.layer2(out)                 # [B, 256, 8, 8]
        out = self.layer3(out)                 # [B, 512, 4, 4]
        out = self.maxpool4(out)               # [B, 512, 1, 1]
        out = self.fc(out)                     # [B, 10, 1, 1]
        out = out.view(out.size(0), -1)        # [B, 10]
        return F.log_softmax(out, dim=-1)

def ResNet_C():
    return ResNet_Custom(BasicBlock_Custom, [1, 0, 1])

# S10 - Resnet for training Tiny Image-net
class BasicBlock_Tiny(nn.Module):
    expansion = 1

    def __init__(self, in_planes, planes, stride=1):
        super(BasicBlock_Tiny, self).__init__()
        self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)

        self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != self.expansion * planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_planes, self.expansion * planes, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(self.expansion * planes)
            )

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        out = F.relu(out)
        return out

class ResNet18_Tiny(nn.Module):
    def __init__(self, block, num_blocks, num_classes=200):
        super(ResNet18_Tiny, self).__init__()
        self.in_planes = 64

        self.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.layer1 = self._make_layer(block, 64, num_blocks[0], stride=1)
        self.layer2 = self._make_layer(block, 128, num_blocks[1], stride=2)
        self.layer3 = self._make_layer(block, 256, num_blocks[2], stride=2)
        self.layer4 = self._make_layer(block, 512, num_blocks[3], stride=2)
        self.Gap1 = nn.AdaptiveAvgPool2d(output_size=(1, 1))
        self.fc = nn.Conv2d(512 * block.expansion, num_classes, kernel_size=1, stride=1, padding=0, bias=False)

    def _make_layer(self, block, planes, num_blocks, stride):
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_planes, planes, stride))
            self.in_planes = planes * block.expansion
        return nn.Sequential(*layers)

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = self.Gap1(out)
        out = self.fc(out)
        out = out.view(out.size(0), -1)
        return F.log_softmax(out, dim=-1)

def ResNet18_TinyImageNet():
    return ResNet18_Tiny(BasicBlock_Tiny, [2, 2, 2, 2])


class Ultimus(nn.Module):

    def __init__(self):
        super(Ultimus, self).__init__()
        self.fc_down = nn.Conv2d(in_channels=48, out_channels=8, kernel_size=(1, 1), padding=0, bias=False)    
        self.fc_up   = nn.Conv2d(in_channels=8, out_channels=48, kernel_size=(1, 1), padding=0, bias=False)

    def forward(self, x):
        k = torch.squeeze(self.fc_down(x), 3)                   # [B, 8, 1, 1] -> [B, 8, 1]
        q = torch.squeeze(self.fc_down(x), 3)                   # [B, 8, 1, 1] -> [B, 8, 1]
        v = torch.squeeze(self.fc_down(x), 3)                   # [B, 8, 1, 1] -> [B, 8, 1]
        q_t = torch.permute(q, (0,2,1))                         # [B, 8, 1] -> [B, 1, 8]   
        AM = F.softmax((torch.matmul(k, q_t))/(8**0.5),dim=-1)   # [B, 8, 1] * [B, 1, 8] -> [B, 8, 8]
        v_t = torch.permute(v, (0, 2, 1))                       # [B, 8, 1] -> [B, 1, 8]
        z = torch.matmul(AM, v)                                 # [B, 8, 8] * [B, 8, 1] -> [B, 8, 1]
        z = torch.unsqueeze(z, 3)                               # [B, 8, 1] -> [B, 8, 1, 1]
        out = self.fc_up(z)                                     # [B, 8, 1, 1] -> [B, 48, 1, 1]
        return out

class basic_attn_model(nn.Module):

    def __init__(self):
        super(basic_attn_model, self).__init__()

        # CONVOLUTION BLOCK 1
        self.convblock1 = nn.Sequential(
            nn.Conv2d(in_channels=3, out_channels=16, kernel_size=(3, 3), padding=1, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(16),
        )  # in = 32x32x3 , out = 32x32x16, RF = 3

        # CONVOLUTION BLOCK 2
        self.convblock2 = nn.Sequential(
            nn.Conv2d(in_channels=16, out_channels=32, kernel_size=(3, 3), padding=1, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(32),
        )  # in = 32x32x16 , out = 32x32x32, RF = 5

        # CONVOLUTION BLOCK 3
        self.convblock3 = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=48, kernel_size=(3, 3), padding=1, bias=False),
            nn.ReLU(),
            nn.BatchNorm2d(48),
        )  # in = 32x32x32 , out = 32x32x48, RF = 7

        # GAP BLOCK
        self.Gap1 = nn.Sequential(
            nn.AvgPool2d(kernel_size=32)
        )  # in = 32x32x48 , out = 1x1x48, RF = 7	, RF = 7

        # ULTIMUS BLOCK
        self.Ultimus = Ultimus()

        self.fc1 = nn.Sequential(
            nn.Conv2d(in_channels=48, out_channels=10, kernel_size=(1, 1), padding=0, bias=False)
        )  # in = 1x1x48 , out = 1x1x10

    def forward(self, x):
        x = self.convblock3(self.convblock2(self.convblock1(x))) # [b, 48, 32, 32]
        x = self.Gap1(x)                                         # [b, 48, 1, 1]
        out = self.Ultimus(x)                                    # [b, 48, 1, 1]
        out = self.Ultimus(out)                                  # [b, 48, 1, 1]
        out = self.Ultimus(out)                                  # [b, 48, 1, 1]
        out = self.Ultimus(out)                                  # [b, 48, 1, 1]
        x = self.fc1(out)                                        # [b, 10, 1, 1]
        x = x.view(-1, 10)                                       # [b, 10]
        return F.log_softmax(x, dim=-1)

# S11 Model for VIT - Modified https://github.com/kentaroy47/vision-transformers-cifar10/blob/main/models/vit.py

def pair(t):
    return t if isinstance(t, tuple) else (t, t)

class PreNorm(nn.Module):
    def __init__(self, dim, numb_patch, fn):
        super().__init__()
        self.norm = nn.LayerNorm([dim, numb_patch, numb_patch])
        self.fn = fn
    def forward(self, x, **kwargs):
        return self.fn(self.norm(x), **kwargs)
    
class FeedForward(nn.Module):
    def __init__(self, dim, hidden_dim, dropout = 0.):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels=dim, out_channels=hidden_dim, kernel_size=(1, 1), padding=0, bias=False),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Conv2d(in_channels=hidden_dim, out_channels=dim, kernel_size=(1, 1), padding=0, bias=False),
            nn.Dropout(dropout)
        )        
    def forward(self, x):
        out = self.net(x)
        return out
    
class Attention(nn.Module):
    def __init__(self, dim, heads = 8, dim_head = 64, dropout = 0.):
        super().__init__()
        inner_dim = dim_head *  heads
        project_out = not (heads == 1 and dim_head == dim)

        self.heads = heads
        self.scale = dim_head ** -0.5
        self.head_channels = dim
        in_channels = dim
        out_channels = dim
        self.attend = nn.Softmax(dim = -1)
        self.to_keys = nn.Conv2d(in_channels, out_channels, 1)
        self.to_queries = nn.Conv2d(in_channels, out_channels, 1)
        self.to_values = nn.Conv2d(in_channels, out_channels, 1)

        self.to_out = nn.Sequential(
            nn.Conv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=(1, 1), padding=0, bias=False),
            nn.Dropout(dropout)
        ) if project_out else nn.Identity()

    def forward(self, x):
        b = x.shape[0]
        k = self.to_keys(x).view(b, self.heads, self.head_channels, -1)
        q = self.to_queries(x).view(b, self.heads, self.head_channels, -1)
        v = self.to_values(x).view(b, self.heads, self.head_channels, -1)
        dots = torch.matmul(q, k.transpose(-1, -2)) * self.scale

        attn = self.attend(dots)

        out = torch.matmul(attn, v)
        out = out.permute(0, 2, 1, 3)
        return self.to_out(out)
    
class Transformer(nn.Module):
    def __init__(self, dim, depth, heads, dim_head, mlp_dim, numb_patch, dropout = 0.):
        super().__init__()
        self.layers = nn.ModuleList([])
        for _ in range(depth):
            self.layers.append(nn.ModuleList([
                PreNorm(dim, numb_patch, Attention(dim, heads = heads, dim_head = dim_head, dropout = dropout)),
                PreNorm(dim, numb_patch, FeedForward(dim, mlp_dim, dropout = dropout))
            ]))
    def forward(self, x):
        for attn, ff in self.layers:
            x = attn(x) + x
            x = ff(x) + x
        return x
    
class ViT(nn.Module):
    def __init__(self, *, image_size, patch_size, num_classes, dim, depth, heads, mlp_dim, numb_patch, 
                 pool = 'cls', channels = 3, dim_head = 64, dropout = 0., emb_dropout = 0.):
        super().__init__()
        image_height, image_width = pair(image_size)
        patch_height, patch_width = pair(patch_size)

        assert image_height % patch_height == 0 and image_width % patch_width == 0, 'Image dimensions must be divisible by the patch size.'

        num_patches = (image_height // patch_height) * (image_width // patch_width)
        self.num_patch = (image_height // patch_height)
        patch_dim = channels * patch_height * patch_width
        assert pool in {'cls', 'mean'}, 'pool type must be either cls (cls token) or mean (mean pooling)'
        
        self.to_patch_embedding = nn.Conv2d(in_channels=channels,
                                            out_channels=patch_dim,
                                            kernel_size=patch_size,
                                            stride=patch_size,
                                            padding=0)

        self.pos_embedding = nn.Parameter(torch.randn(1, patch_dim + 1, self.num_patch, self.num_patch))
        self.dropout = nn.Dropout(emb_dropout)

        self.transformer = Transformer(dim, depth, heads, dim_head, mlp_dim, numb_patch, dropout)

        self.pool = pool
        self.to_latent = nn.Identity()

        self.mlp_head = nn.Sequential(
            nn.LayerNorm([num_patches, 1, 1]),
            nn.Conv2d(in_channels=num_patches, out_channels=num_classes, kernel_size=(1, 1), padding=0, bias=False)
        )
        self.flatten = nn.Flatten(start_dim=2, end_dim=3)


    def forward(self, img):
        x = self.to_patch_embedding(img)
        b, _, _, _ = x.shape

        cls_tokens = nn.Parameter(torch.ones(b, 1, self.num_patch, self.num_patch),requires_grad=True)
        cls_tokens = cls_tokens.to(device='cuda')
        x = torch.cat((cls_tokens, x), dim=1)
        
        x += self.pos_embedding

        x = self.dropout(x)

        x = self.transformer(x)
        x = self.flatten(x)
        x = x[:, 0]
        x = self.to_latent(x)
        x = torch.unsqueeze(x, 2)
        x = torch.unsqueeze(x, 3)
        out = self.mlp_head(x)
        out = out.view(-1, 10)
        return out