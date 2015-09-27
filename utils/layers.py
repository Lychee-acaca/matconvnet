from collections import OrderedDict
from math import floor, ceil
import numpy as np
from numpy import array
import scipy
import scipy.io
import scipy.misc

layers_type = {}
layers_type[0]  = 'none'
layers_type[1]  = 'accuracy'
layers_type[2]  = 'bnll'
layers_type[3]  = 'concat'
layers_type[4]  = 'conv'
layers_type[5]  = 'data'
layers_type[6]  = 'dropout'
layers_type[7]  = 'euclidean_loss'
layers_type[8]  = 'flatten'
layers_type[9]  = 'hdf5_data'
layers_type[10] = 'hdf5_output'
layers_type[28] = 'hinge_loss'
layers_type[11] = 'im2col'
layers_type[12] = 'image_data'
layers_type[13] = 'infogain_loss'
layers_type[14] = 'inner_product'
layers_type[15] = 'lrn'
layers_type[25] = 'eltwise'
layers_type[29] = 'memory_data'
layers_type[16] = 'multinomial_logistic_loss'
layers_type[17] = 'pool'
layers_type[26] = 'power'
layers_type[18] = 'relu'
layers_type[19] = 'sigmoid'
layers_type[27] = 'sigmoid_cross_entropy_loss'
layers_type[20] = 'softmax'
layers_type[21] = 'softmax_loss'
layers_type[22] = 'split'
layers_type[23] = 'tanh'
layers_type[24] = 'window_data'
layers_type[39] = 'deconvolution'
layers_type[40] = 'crop'

def getFilterOutputSize(size, kernelSize, stride, pad):
    return [floor((size[0] + pad[0]+pad[1] - kernelSize[0]) / stride[0]) + 1., \
            floor((size[1] + pad[2]+pad[3] - kernelSize[1]) / stride[1]) + 1.]

def getFilterTransform(ks, stride, pad):
    y1 = 1. - pad[0] ;
    y2 = 1. - pad[0] + ks[0] - 1 ;
    x1 = 1. - pad[2] ;
    x2 = 1. - pad[2] + ks[1] - 1 ;
    h = y2 - y1 + 1. ;
    w = x2 - x1 + 1. ;
    return CaffeTransform([h, w], stride, [(y1+y2)/2, (x1+x2)/2])

def reorder(aList, order):
    return [aList[i] for i in order]

def row(x):
  return np.array(x,dtype=float).reshape(1,-1)

def rowarray(x):
  return x.reshape(1,-1)

def rowcell(x):
    return np.array(x,dtype=object).reshape(1,-1)

def dictToMatlabStruct(d):
  if not d:
    return np.zeros((0,))
  dt = []
  for x in d.keys():
      pair = (x,object)
      if isinstance(d[x], np.ndarray): pair = (x,type(d[x]))
      dt.append(pair)
  y = np.empty((1,),dtype=dt)
  for x in d.keys():
    y[x][0] = d[x]
  return y

# --------------------------------------------------------------------
#                                                  MatConvNet in NumPy
# --------------------------------------------------------------------

mlayerdt = [('name',object),
            ('type',object),
            ('inputs',object),
            ('outputs',object),
            ('params',object),
            ('block',object)]

mparamdt = [('name',object),
            ('value',object)]

# --------------------------------------------------------------------
#                                                      Vars and params
# --------------------------------------------------------------------

class CaffeBuffer(object):
    def __init__(self, name):
        self.name = name
        self.size = None
        self.value = np.zeros((0,))
        self.bgrInput = False

    def toMatlab(self):
        mparam = np.empty(shape=[1,], dtype=mparamdt)
        mparam['name'][0] = self.name
        mparam['value'][0] = self.value
        return mparam

class CaffeTransform(object):
    def __init__(self, size, stride, offset):
        self.size = size
        self.stride = stride
        self.offset = offset

    def __str__(self):
        return "<%s %s %s>" % (self.size, self.stride, self.offset)

def composeTransforms(a, b):
    size = [0.,0.]
    stride = [0.,0.]
    offset = [0.,0.]
    for i in [0,1]:
        size[i] = a.stride[i] * (b.size[i] - 1) + a.size[i]
        stride[i] = a.stride[i] * b.stride[i]
        offset[i] = a.stride[i] * (b.offset[i] - 1) + a.offset[i]
    c = CaffeTransform(size, stride, offset)
    return c

def transposeTransform(a):
    size = [0.,0.]
    stride = [0.,0.]
    offset = [0.,0.]
    for i in [0,1]:
        size[i] = (a.size[i] + a.stride[i] - 1.0) / a.stride[i]
        stride[i] = 1.0/a.stride[i]
        offset[i] = (1.0 + a.stride[i] - a.offset[i])/a.stride[i]
    c = CaffeTransform(size, stride, offset)
    return c

# --------------------------------------------------------------------
#                                                               Layers
# --------------------------------------------------------------------

class CaffeLayer(object):
    def __init__(self, name, inputs, outputs):
        self.name = name
        self.inputs = inputs
        self.outputs = outputs
        self.params = []

    def reshape(self, model):
        pass

    def display(self):
        print "Layer ", self.name
        print "  Inputs: %s" % (self.inputs,)
        print "  Outputs: %s" % (self.outputs,)
        print "  Params: %s" % (self.params,)

    def getTransforms(self, model):
        transforms = []
        for i in enumerate(self.inputs):
            row = []
            for j in enumerate(self.outputs):
                row.append(CaffeTransform([1.,1.], [1.,1.], [1.,1.]))
            transforms.append(row)
        return transforms

    def transpose(self, model):
        pass

    def toMatlab(self):
        mlayer = np.empty(shape=[1,],dtype=mlayerdt)
        mlayer['name'][0] = self.name
        mlayer['type'][0] = None
        mlayer['inputs'][0] = rowcell(self.inputs)
        mlayer['outputs'][0] = rowcell(self.outputs)
        mlayer['params'][0] = rowcell(self.params)
        mlayer['block'][0] = dictToMatlabStruct({})
        return mlayer

class CaffeElementWise(CaffeLayer):
    def reshape(self, model):
        for i in range(len(self.inputs)):
            model.vars[self.outputs[i]].size = \
                model.vars[self.inputs[i]].size

class CaffeReLU(CaffeElementWise):
    def __init__(self, name, inputs, outputs):
        super(CaffeReLU, self).__init__(name, inputs, outputs)

    def toMatlab(self):
        mlayer = super(CaffeReLU, self).toMatlab()
        mlayer['type'] = u'dagnn.ReLU'
        return mlayer

class CaffeSoftMax(CaffeElementWise):
    def __init__(self, name, inputs, outputs):
        super(CaffeSoftMax, self).__init__(name, inputs, outputs)

    def toMatlab(self):
        mlayer = super(CaffeSoftMax, self).toMatlab()
        mlayer['type'] = u'dagnn.SofMax'
        return mlayer

class CaffeSoftMaxLoss(CaffeElementWise):
    def __init__(self, name, inputs, outputs):
        super(CaffeSoftMaxLoss, self).__init__(name, inputs, outputs)

    def toMatlab(self):
        mlayer = super(CaffeSoftMaxLoss, self).toMatlab()
        mlayer['type'] = u'dagnn.SoftMaxLoss'
        return mlayer

class CaffeDropout(CaffeElementWise):
    def __init__(self, name, inputs, outputs, ratio):
        super(CaffeDropout, self).__init__(name, inputs, outputs)
        self.ratio = ratio

    def toMatlab(self):
        mlayer = super(CaffeDropout, self).toMatlab()
        mlayer['type'][0] = u'dagnn.DropOut'
        mlayer['block'][0] = dictToMatlabStruct({'rate': float(self.ratio)})
        return mlayer

    def display(self):
        super(CaffeDropout, self).display()
        print "  Ratio (rate): ", self.ratio

# --------------------------------------------------------------------
#                                                          Convolution
# --------------------------------------------------------------------

class CaffeConv(CaffeLayer):
    def __init__(self, name, inputs, outputs, kernelSize, hasBias, numFilters, numFilterGroups, stride, pad):
        super(CaffeConv, self).__init__(name, inputs, outputs)
        self.params = [name + 'f']
        if hasBias: self.params.append(name + 'b')
        self.hasBias = hasBias
        self.kernelSize = kernelSize
        self.numFilters = numFilters
        self.numFilterGroups = numFilterGroups
        self.filterDimension = None
        self.stride = stride
        self.pad = pad

    def display(self):
        super(CaffeConv, self).display()
        print "  Kernel Size: %s" % self.kernelSize
        print "  Has Bias: %s" % self.hasBias
        print "  Pad: %s" % (self.pad,)
        print "  Stride: %s" % (self.stride,)
        print "  Num Filters: %s" % self.numFilters
        print "  Filter Dimension", self.filterDimension

    def reshape(self, model):
        if len(model.vars[self.inputs[0]].size) == 0: return
        model.vars[self.outputs[0]].size = \
            getFilterOutputSize(model.vars[self.inputs[0]].size[0:2],
                                self.kernelSize, self.stride, self.pad) + \
            [self.numFilters, model.vars[self.inputs[0]].size[3]]
        self.filterDimension = \
            model.vars[self.inputs[0]].size[2] / self.numFilterGroups

    def getTransforms(self, model):
        return [[getFilterTransform(self.kernelSize, self.stride, self.pad)]]

    def transpose(self, model):
        self.kernelSize = reorder(self.kernelSize, [1,0])
        self.stride = reorder(self.stride, [1,0])
        self.pad = reorder(self.pad, [1,0,3,2])
        print model.params[self.params[0]].value
        if model.params[self.params[0]].value.size > 0:
            print "Layer %s transposing filters" % self.name
            param = model.params[self.params[0]]
            param.value = param.value.transpose([1,0,2,3])
            if model.vars[self.inputs[0]].bgrInput:
                print "Layer %s BGR to RGB conversion" % self.name
                param.value = param.value[:,:,: : -1,:]

    def toMatlab(self):
        size = self.kernelSize + [self.filterDimension, self.numFilters]
        mlayer = super(CaffeConv, self).toMatlab()
        mlayer['type'][0] = u'dagnn.Conv'
        mlayer['block'][0] = dictToMatlabStruct(
            {'hasBias': self.hasBias,
             'size': row(size),
             'pad': row(self.pad),
             'stride': row(self.stride)})
        return mlayer

# --------------------------------------------------------------------
#                                                        Deconvolution
# --------------------------------------------------------------------

class CaffeDeconvolution(CaffeConv):
    def __init__(self, name, inputs, outputs, kernelSize, hasBias, numFilters, numFilterGroups, stride, pad):
        super(CaffeDeconvolution, self).__init__(name, inputs, outputs, kernelSize, hasBias, numFilters, numFilterGroups, stride, pad)

    def display(self):
        super(CaffeDeconvolution, self).display()

    def reshape(self, model):
        if len(model.vars[self.inputs[0]].size) == 0: return
        model.vars[self.outputs[0]].size = \
            getFilterOutputSize(model.vars[self.inputs[0]].size[0:2],
                                self.kernelSize, self.stride, self.pad) + \
            [self.numFilters, model.vars[self.inputs[0]].size[3]]
        self.filterDimension = model.vars[self.inputs[0]].size[2]

    def getTransforms(self, model):
        t = getFilterTransform(self.kernelSize, self.stride, self.pad)
        t = transposeTransform(t)
        return [[t]]

    def transpose(self, model):
        self.kernelSize = reorder(self.kernelSize, [1,0])
        self.stride = reorder(self.stride, [1,0])
        self.pad = reorder(self.pad, [1,0,3,2])
        if model.params[self.params[0]].value.size > 0:
            print "Layer %s transposing filters" % self.name
            param = model.params[self.params[0]]
            param.value = param.value.transpose([1,0,2,3])
            if model.vars[self.inputs[0]].bgrInput:
                print "Layer %s BGR to RGB conversion" % self.name
                param.value = param.value[:,:,:,: : -1]

    def toMatlab(self):
        size = self.kernelSize +  [self.numFilters, \
                                      self.filterDimension / self.numFilterGroups]
        mlayer = super(CaffeDeconvolution, self).toMatlab()
        mlayer['type'][0] = u'dagnn.ConvTranspose'
        mlayer['block'][0] = dictToMatlabStruct(
            {'hasBias': self.hasBias,
             'size': row(size),
             'upsample': row(self.stride),
             'crop': row(self.pad)})
        return mlayer

# --------------------------------------------------------------------
#                                                              Pooling
# --------------------------------------------------------------------

class CaffePooling(CaffeLayer):
    def __init__(self, name, inputs, outputs, method, kernelSize, stride, pad):
        super(CaffePooling, self).__init__(name, inputs, outputs)
        self.method = method
        self.kernelSize = kernelSize
        self.stride = stride
        self.pad = pad
        self.padCorrected = []

    def display(self):
        super(CaffePooling, self).display()
        print "  Method: ", self.method
        print "  Kernel Size: %s" % self.kernelSize
        print "  Pad: %s" % (self.pad,)
        print "  PadCorrected: %s" % (self.padCorrected,)
        print "  Stride: %s" % (self.stride,)

    def reshape(self, model):
        if len(model.vars[self.inputs[0]].size) == 0: return
        size = model.vars[self.inputs[0]].size
        ks = self.kernelSize
        stride = self.stride
        # MatConvNet uses a slighly different definition of padding, which we think
        # is the correct one (it corresponds to the filters)
        self.padCorrected = self.pad
        for i in [0, 1]:
            self.padCorrected[1 + i*2] += \
                ceil((size[i] - ks[i])/float(stride[i]))*stride[i] + ks[i] - size[i]
        model.vars[self.outputs[0]].size = \
            getFilterOutputSize(size[0:2], ks, self.stride, self.padCorrected) + \
            size[2:4]

    def getTransforms(self, model):
        return [[getFilterTransform(self.kernelSize, self.stride, self.pad)]]

    def transpose(self, model):
        self.kernelSize = reorder(self.kernelSize, [1,0])
        self.stride = reorder(self.stride, [1,0])
        self.pad = reorder(self.pad, [1,0,3,2])

    def toMatlab(self):
        mlayer = super(CaffePooling, self).toMatlab()
        mlayer['type'][0] = u'dagnn.Pooling'
        mlayer['block'][0] = dictToMatlabStruct(
            {'poolSize': row(self.kernelSize),
             'stride': row(self.stride),
             'pad': row(self.padCorrected)})
        return mlayer

class CaffeInnerProduct(CaffeLayer):
    def __init__(self, name, inputs, outputs, paramValues):
        super(CaffeInnerProduct, self).__init__(name, inputs, outputs)
        self.params =  [name + x for x in ['f' 'b']]
        self.paramValues = paramValues

    def reshape(self):
        assert(false) # we need to reshape the parameter arrays?

# --------------------------------------------------------------------
#                                                         Other Layers
# --------------------------------------------------------------------

class CaffeConcat(CaffeLayer):
    def __init__(self, name, inputs, outputs, concatDim):
        super(CaffeConcat, self).__init__(name, inputs, outputs)
        self.concatDim = concatDim

    def transpose(self, model):
        self.concatDim = [1, 0, 2, 3][self.concatDim]

    def toMatlab(self):
        mlayer = super(CaffeConcat, self).toMatlab()
        mlayer['type'][0] = u'dagnn.Concat'
        mlayer['block'][0] = dictToMatlabStruct({'dim': float(self.concatDim)})
        return mlayer

class CaffeEltWise(CaffeElementWise):
    def __init__(self, name, inputs, outputs, operation, coeff, stableProdGrad):
        super(CaffeEltWise, self).__init__(name, inputs, outputs)
        self.operation = operation
        self.coeff = coeff
        self.stableProdGrad = stableProdGrad

    def toMatlab(self):
        mlayer = super(CaffeEltWise, self).toMatlab()
        if self.operation == 'sum':
            mlayer['type'][0] = u'dagnn.Sum'
        else:
            # not implemented
            assert(False)
        return mlayer

    def display(self):
        super(CaffeEltWise, self).display()
        print "  Operation: ", self.operation
        print "  Coeff: %s" % self.coeff
        print "  Stable Prod Grad: %s" % self.stableProdGrad

    def reshape(self, model):
        model.vars[self.outputs[0]].size = \
            model.vars[self.inputs[0]].size
        for i in range(1, len(self.inputs)):
            assert(model.vars[self.inputs[0]].size == model.vars[self.inputs[i]].size)

class CaffeCrop(CaffeLayer):
    def __init__(self, name, inputs, outputs):
        super(CaffeCrop, self).__init__(name, inputs, outputs)
        self.crop = []

    def display(self):
        super(CaffeCrop, self).display()
        print "  Crop: %s" % self.crop

    def reshape(self, model):
        # this is quite complex as we need to compute on the fly
        # the geometry
        tfs1 = model.getParentTransforms(self.inputs[0], self.name)
        tfs2 = model.getParentTransforms(self.inputs[1], self.name)

        print
        print self.name, self.inputs[0]
        for a,x in enumerate(tfs1): print "%10s %s" % (x,tfs1[x])
        print self.name, self.inputs[1]
        for a,x in enumerate(tfs2): print "%10s %s" % (x,tfs2[x])

        # the goal is to crop inputs[0] to make it as big as inputs[1] and
        # aligned to it; so now we find the map from inputs[0] to inputs[1]

        tf = None
        for name, tf2 in tfs2.items():
            if tfs1.has_key(name):
                tf1 = tfs1[name]
                tf = composeTransforms(transposeTransform(tf2), tf1)
                break
        if tf is None:
            print "Error: could not find common ancestor for inputs '%s' and '%s' of the CaffeCrop layer '%s'" % (self.inputs[0], self.inputs[1], self.name)
            sys.exit(1)
        print "  Transformation %s -> %s = %s" % (self.inputs[0],
                                                  self.inputs[1], tf)
        # for this to make sense it shoudl be tf.stride = 1
        assert(tf.stride[0] == 1 and tf.stride[1] == 1)

        # finally we can get the crops!
        self.crop = [0.,0.]
        for i in [0,1]:
            # i' = alpha (i - 1) + beta + crop = 1 for i = 1
            # crop = 1 - beta
            self.crop[i] =  round(1 - tf.offset[i])
        print "  Crop %s" % self.crop

        # print
        # print "resolved"
        # tfs3 = model.getParentTransforms(self.outputs[0])
        # for a,x in enumerate(tfs3): print "%10s %s" % (x,tfs3[x])

        # now compute output variable size, which will be the size of the second input
        model.vars[self.outputs[0]].size = model.vars[self.inputs[1]].size

    def getTransforms(self, model):
        t = CaffeTransform([1.,1.], [1.,1.], [1.+self.crop[0],1.+self.crop[1]])
        return [[t],[None]]

    def toMatlab(self):
        mlayer = super(CaffeCrop, self).toMatlab()
        mlayer['type'][0] = u'dagnn.Crop'
        mlayer['block'][0] = dictToMatlabStruct({'crop': row(self.crop)})
        return mlayer

class CaffeData(CaffeLayer):
    def __init__(self, name, inputs, outputs, size):
        super(CaffeData, self).__init__(name, inputs, outputs)
        self.size = size

# --------------------------------------------------------------------
#                                                     Helper functions
# --------------------------------------------------------------------

class CaffeModel(object):
    def __init__(self):
        self.layers = OrderedDict()
        self.vars = OrderedDict()
        self.params = OrderedDict()

    def addLayer(self, layer):
        ename = layer.name
        while self.layers.has_key(ename):
            ename = ename + 'x'
        if layer.name != ename:
            print "Warning: a layer with name %s was already found, using %s instead" % \
                (layer.name, ename)
            layer.name = ename
        for v in layer.inputs:  self.addVar(v)
        for v in layer.outputs: self.addVar(v)
        for p in layer.params: self.addParam(p)
        self.layers[layer.name] = layer

    def addVar(self, name):
        if not self.vars.has_key(name):
            self.vars[name] = CaffeBuffer(name)

    def addParam(self, name):
        if not self.params.has_key(name):
            self.params[name] = CaffeBuffer(name)

    def renameLayer(self, old, new):
        self.layers[old].name = new
        # reinsert layer with new name -- this mess is to preserve the order
        layers = OrderedDict([(new,v) if k==old else (k,v)
                              for k,v in self.layers.items()])
        self.layers = layers

    def renameVar(self, old, new, afterLayer=None):
        self.vars[old].name = new
        if afterLayer is not None:
            start = self.layers.keys().index(afterLayer) + 1
        else:
            start = 0
        # fix all references to the variable
        for layer in self.layers.values()[start:-1]:
            layer.inputs = [new if x==old else x for x in layer.inputs]
            layer.outputs = [new if x==old else x for x in layer.outputs]
        var = self.vars[old]
        del self.vars[old]
        self.vars[new] = var

    def renameParam(self, old, new):
        self.params[old].name = new
        # fix all references to the variable
        for layer in self.layers.itervalues():
            layer.params = [new if x==old else x for x in layer.params]
        var = self.params[old]
        del self.params[old]
        self.params[new] = var

    def removeParam(self, name):
        del net.params[name]

    def removeLayer(self, name):
        # todo: fix this stuff for weight sharing
        layer = self.layers[name]
        for paramName in layer.params:
            self.removeParam(paramName)
        del self.layers[name]

    def reshape(self):
        for layer in self.layers.itervalues():
            layer.reshape(self)

    def display(self):
        for layer in self.layers.itervalues():
            layer.display()
        for var in self.vars.itervalues():
            print 'Variable ', var.name
            print '       size: %s' % (var.size,)
        for par in self.params.itervalues():
            print 'Parameter ', par.name
            print '       size: %s' % (par.size,)
            print ' data found: %s' % (par.value is not None,)

    def transpose(self):
        for layer in self.layers.itervalues():
            layer.transpose(self)

    def getParentTransforms(self, variableName, topLayerName=None):
        layerNames = self.layers.keys()
        if topLayerName:
            layerIndex = layerNames.index(topLayerName)
        else:
            layerIndex = len(self.layers) + 1
        transforms = OrderedDict()
        transforms[variableName] = CaffeTransform([1.,1.], [1.,1.], [1.,1.])
        for layerName in reversed(layerNames[0:layerIndex]):
            layer = self.layers[layerName]
            layerTfs = layer.getTransforms(self)
            for i, inputName in enumerate(layer.inputs):
                tfs = []
                if transforms.has_key(inputName):
                    tfs.append(transforms[inputName])
                for j, outputName in enumerate(layer.outputs):
                    if layerTfs[i][j] is None: continue
                    if transforms.has_key(outputName):
                        composed = composeTransforms(layerTfs[i][j], transforms[outputName])
                        tfs.append(composed)

                if len(tfs) > 0:
                    # should resolve conflicts, not simply pick the first tf
                    transforms[inputName] = tfs[0]
        return transforms
