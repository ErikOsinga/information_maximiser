import tensorflow as tf
import numpy as np
import tqdm
import utils

class IMNN():
    def __init__(n, parameters):
        # INITIALISE NETWORK PARAMETERS
        #______________________________________________________________
        # INPUTS
        # parameters                    dict      - dictionary containing initialisation parameters
        #______________________________________________________________
        # FUNCTIONS (DEFINED IN utils.py)
        # check_params(dict)                      - checks that all necessary parameters are in dictionary
        # isboolean(list)               bool      - checks that parameter is a boolean
        # positive_integer(list)        int       - checks that parameter is a positive integer
        # number_of_derivative_simulations(dict, class)
        #                                         - calculates the number of simulations to use for numerical derivative
        # inputs(dict)                  int/list  - checks shape of network input
        # check_save_file(dict)         str/None  - checks that file name is a string or None
        # isfloat(list)                 float     - checks that parameter is a float
        # check_prebuild_params(dict)             - checks that all parameters for prebuilt network are in dictionary
        # auto_initialise(float)        bool      - switch to choose whether to use constant weight variance
        # activation(dict)              tf func   - checks that TF activation function is allowed
        #                               bool
        #                               float/int
        # hidden_layers(dict, class)    list      - checks that hidden layers can be built into a network
        # initialise_variables()        11 Nones  - sets all other class variables to None
        #______________________________________________________________
        # VARIABLES
        # u                             class     - utility functions
        # _FLOATX                     n tf type   - set TensorFlow types to 32 bit (for GPU)
        # verbose                     n bool      - True to print outputs such as shape of tensors
        # n_params                    n int       - number of parameters in the model
        # n_s                         n int       - number of simulations in each combination
        # n_p                         n int       - number of differentiation simulations
        # n_summaries                 n int       - number of outputs from the network
        # inputs                      n int/list  - number of inputs (int) or shape of input (list)
        # η                           n float     - learning rate
        # prebuild                    n bool      - True to allow IMNN to build the network
        # save_file                   n str/None  - Name to save or load graph. None does not save graph
        # get_MLE                     n bool      - True to calculate MLE
        # wv                          n float     - weight variance to initialise all weights
        # allow_init                  n bool      - True if nw < 0 so network calculates weight variance
        # bb                          n float     - constant bias initialiser value
        # activation                  n tf func   - activation function to use
        # take_α                      n bool      - True is an extra parameter is needed in the activation function
        # α                           n float/int - extra parameter if needed for activation function (can be None)
        # layers                      n list      - contains the neural architecture of the network
        # sess        begin_session() n session   - interactive tensorflow session (with initialised parameters)
        # x                   setup() n tensor    - fiducial simulation input tensor
        # x_real              setup() n tensor    - extra feedforward input tensor for calculating MLE
        # θ_fid               setup() n tensor    - fiducial parameter input tensor for calculation MLE
        # prior                       n tensor    - prior range for each parameter for calculating MLE
        # x_m                 setup() n tensor    - below fiducial simulation input tensor
        # x_p                 setup() n tensor    - above fiducial simulation input tensor
        # dd                  setup() n tensor    - inverse difference between upper and lower parameter value
        # dropout             setup() n tensor    - keep rate for dropout layer
        # output              setup() n tensor    - network output for simulations at fiducial parameter value
        # F                   setup() n tensor    - Fisher information matrix
        # MLE                 setup() n tensor    - MLE of parameters
        # backpropagate       setup() n tf opt    - minimisation scheme for the network
        # μ                  Fisher() n tensor    - mean of network outputs for fiducial simulations
        # C                  Fisher() n tensor    - covariance of network outputs for fiducial simulations
        # iC                 Fisher() n tensor    - inverse covariance of network outputs for fiducial simulations
        # dμdθ               Fisher() n tensor    - numerical derivative of the mean of network outputs
        #______________________________________________________________
        u = utils.utils()
        n._FLOATX = tf.float32
        u.check_params(parameters)
        n.verbose = u.isboolean([parameters, 'verbose'])
        n.n_s = u.positive_integer([parameters, 'number of simulations'])
        n.n_params = u.positive_integer([parameters, 'number of parameters'])
        n.n_p = u.number_of_derivative_simulations(parameters, n)
        n.n_summaries = u.positive_integer([parameters, 'number of summaries'])
        n.inputs = u.inputs(parameters)
        n.prebuild = u.isboolean([parameters, 'prebuild'])
        n.save_file = u.check_save_file([parameters, 'save file'])
        n.get_MLE = u.isboolean([parameters, 'calculate MLE'])
        if n.prebuild:
            u.check_prebuild_params(parameters)
            n.wv = u.isfloat([parameters, 'wv'])
            n.allow_init = u.auto_initialise(n.wv)
            n.bb = u.isfloat([parameters, 'bb'])
            n.activation, n.takes_α, n.α = u.activation(parameters)
            n.layers = u.hidden_layers(parameters, n)
        n.sess, n.x, n.x_real, n.θ_fid, n.prior, n.x_m, n.x_p, n.dd, n.dropout, n.output, n.F, n.backpropagate, n.μ, n.C, n.iC, n.dμdθ, n.MLE, n.AL = u.initialise_variables()

    def begin_session(n):
        # BEGIN TENSORFLOW SESSION AND INITIALISE PARAMETERS
        #______________________________________________________________
        # CALLED FROM (DEFINED IN IMNN.py)
        # setup(optional func)                    - builds generic or auto built network
        # save_network(optional Bool)             - saves the network (if n.save_file is not None)
        #______________________________________________________________
        # VARIABLES
        # config                                  - tensorflow GPU configuration options
        # sess                        n session   - tensorflow session (with initialised parameters)
        #______________________________________________________________
        config = tf.ConfigProto()
        config.gpu_options.allow_growth = True
        n.sess = tf.Session(config = config)
        n.sess.run(tf.global_variables_initializer())
        n.save_network(first_time = True)

    def reinitialise_session(n):
        # REINITIALISE PARAMETERS
        #______________________________________________________________
        # CALLED FROM (DEFINED IN IMNN.py)
        # restore_network(string, float)          - restores network from a tensorflow saver metafile
        #______________________________________________________________
        # VARIABLES
        # sess                        n session   - interactive tensorflow session
        #______________________________________________________________
        n.sess.run(tf.global_variables_initializer())

    def save_network(n, first_time = False):
        # SAVE NETWORK AS A TENSORFLOW SAVER METAFILE
        #______________________________________________________________
        # INPUTS
        # save_file                   n str/None  - name of the file to reload (ending in .meta)
        # first_time                    bool      - whether to save the meta graph or not
        #______________________________________________________________
        # VARIABLES
        # saver                       n tf op     - saving operation from tensorflow
        #______________________________________________________________
        if n.save_file is not None:
            if first_time:
                n.saver = tf.train.Saver()
                n.saver.save(n.sess, "./" + n.save_file)
            else:
                n.saver.save(n.sess, "./" + n.save_file, write_meta_graph = False)

    def restore_network(n):
        # RESTORES NETWORK FROM TENSORFLOW SAVER METAFILE
        #______________________________________________________________
        # INPUTS
        # file                          string    - name of the file to reload (ending in .meta)
        #______________________________________________________________
        # VARIABLES
        # sess                        n session   - interactive tensorflow session (with initialised parameters)
        # save_file                   n string    - name of the file to reload (ending in .meta)
        # loader                        tf op     - loading operation from tensorflow
        # x                           n tensor    - fiducial simulation input tensor
        # x_m                         n tensor    - below fiducial simulation input tensor
        # x_p                         n tensor    - above fiducial simulation input tensor
        # dd                          n tensor    - inverse difference between upper and lower parameter value
        # dropout                     n tensor    - keep rate for dropout layer
        # output                      n tensor    - network output for simulations at fiducial parameter value
        # F                           n tensor    - Fisher information matrix
        # backpropagate               n tf opt    - minimisation scheme for the network
        # C                           n tensor    - covariance of network outputs for fiducial simulations
        # dμdθ                        n tensor    - numerical derivative of the mean of network outputs
        if n.save_file is not None:
            config = tf.ConfigProto()
            config.gpu_options.allow_growth = True
            n.sess = tf.Session(config = config)
            loader = tf.train.import_meta_graph("./" + n.save_file + ".meta")
            loader.restore(n.sess, n.save_file)
            n.x = tf.get_default_graph().get_tensor_by_name("x:0")
            n.x_m = tf.get_default_graph().get_tensor_by_name("x_m:0")
            n.x_p = tf.get_default_graph().get_tensor_by_name("x_p:0")
            n.dd = tf.get_default_graph().get_tensor_by_name("dd:0")
            n.dropout = tf.get_default_graph().get_tensor_by_name("dropout:0")
            n.output = tf.get_default_graph().get_tensor_by_name("output:0")
            n.F = tf.get_default_graph().get_tensor_by_name("fisher_information:0")
            n.C = tf.get_default_graph().get_tensor_by_name("central_covariance:0")
            n.dμdθ = tf.get_default_graph().get_tensor_by_name("mean_derivative:0")
            n.backpropagate = tf.get_default_graph().get_operation_by_name("Adam")

    def dense(n, input_tensor, l, dropout):
        # DENSE LAYER
        #______________________________________________________________
        # CALLED FROM (DEFINED IN IMNN.py)
        # build_network(tensor, tensor) tensor    - auto builds predefined network
        #______________________________________________________________
        # RETURNS
        # tensor
        # activated dense output (with dropout)
        #______________________________________________________________
        # INPUTS
        # input_tensor                  tensor    - input tensor to the dense layer
        # l                             int       - layer counter
        # dropout                       tensor    - keep rate for dropout layer
        # layers                      n list      - contains the neural architecture of the network
        # allow_init                  n bool      - True is nw = 0. so network calculates weight variance
        # wv                          n float     - weight variance to initialise the weights
        # bb                          n float     - bias initialiser value
        # n.take_α                    n bool      - True is an extra parameter is needed in the activation function
        # activation                  n tf func   - activation function to use
        # n.α                         n float/int - extra parameter if needed for activation function (can be None)
        #______________________________________________________________
        # VARIABLES
        # previous_layer                int       - shape of previous layer
        # weight_shape                  tuple     - shape of the weight kernel
        # bias_shape                    tuple     - shape of the bias kernel
        # weights                       tensor    - weight kernel
        # biases                        tensor    - bias kernel
        # dense                         tensor    - dense layer (not activated)
        #______________________________________________________________
        previous_layer = int(input_tensor.get_shape()[-1])
        weight_shape = (previous_layer, n.layers[l])
        bias_shape = (n.layers[l])
        if n.allow_init:
            n.wv = np.sqrt(2. / previous_layer)
        weights = tf.get_variable("weights", weight_shape, initializer = tf.random_normal_initializer(0., n.wv))
        biases = tf.get_variable("biases", bias_shape, initializer = tf.constant_initializer(n.bb))
        dense = tf.add(tf.matmul(input_tensor, weights), biases)
        if n.takes_α:
            return tf.nn.dropout(n.activation(dense, n.α), dropout, name = 'dense_' + str(l))
        else:
            return tf.nn.dropout(n.activation(dense), dropout, name = 'dense_' + str(l))

    def conv(n, input_tensor, l, dropout):
        # CONVOLUTIONAL LAYER
        #______________________________________________________________
        # CALLED FROM (DEFINED IN IMNN.py)
        # build_network(tensor, tensor) tensor    - auto builds predefined network
        #______________________________________________________________
        # RETURNS
        # tensor
        # activated convolutional output (with dropout)
        #______________________________________________________________
        # INPUTS
        # input_tensor                  tensor    - input tensor to the convolutional layer
        # l                             int       - layer counter
        # dropout                       tensor    - keep rate for dropout layer
        # layers                      n list      - contains the neural architecture of the network
        # allow_init                  n bool      - True is nw = 0. so network calculates weight variance
        # wv                          n float     - weight variance to initialise the weights
        # bb                          n float     - bias initialiser value
        # n.take_α                    n bool      - True is an extra parameter is needed in the activation function
        # activation                  n tf func   - activation function to use
        # n.α                         n float/int - extra parameter if needed for activation function (can be None)
        #______________________________________________________________
        # VARIABLES
        # previous_layer                int       - shape of previous layer
        # weight_shape                  tuple     - shape of the weight kernel
        # bias_shape                    tuple     - shape of the bias kernel
        # weights                       tensor    - weight kernel
        # biases                        tensor    - bias kernel
        # conv                          tensor    - convolutional feature map (not activated)
        #______________________________________________________________
        previous_filters = int(input_tensor.get_shape()[-1])
        if len(n.layers[l][1]) == 2:
            convolution = tf.nn.conv2d
            weight_shape = (n.layers[l][1][0], n.layers[l][1][1], previous_filters, n.layers[l][0])
        else:
            convolution = tf.nn.conv3d
            weight_shape = (n.layers[l][1][0], n.layers[l][1][1], n.layers[l][1][1], previous_filters, n.layers[l][0])
        bias_shape = (n.layers[l][0])
        if n.allow_init:
            n.wv = np.sqrt(2. / previous_filters)
        weights = tf.get_variable("weights", weight_shape, initializer = tf.random_normal_initializer(0., n.wv))
        biases = tf.get_variable("biases", bias_shape, initializer = tf.constant_initializer(n.bb))
        conv = tf.add(convolution(input_tensor, weights, [1] + n.layers[l][2] + [1], padding = n.layers[l][3]), biases)
        if n.takes_α:
            return tf.nn.dropout(n.activation(conv, n.α), dropout, name = 'conv_' + str(l))
        else:
            return tf.nn.dropout(n.activation(conv), dropout, name = 'conv_' + str(l))

    def build_network(n, input_tensor, dropout):
        # AUTO BUILD NETWORK
        #______________________________________________________________
        # CALLED FROM (DEFINED IN IMNN.py)
        # setup(optional func)                    - builds generic or auto built network
        #______________________________________________________________
        # RETURNS
        # tensor
        # last tensor of the IMNN architecture (summarised output)
        #______________________________________________________________
        # FUNCTIONS (DEFINED IN IMNN.py)
        # dense(tensor, int, tensor)    tensor    - calculates a dense layer
        # conv(tensor, int, tensor)     tensor    - calculates a convolutional layer
        #______________________________________________________________
        # INPUTS
        # input_tensor                  tensor    - input tensor to the network
        # dropout                       tensor    - keep rate for dropout layer
        # verbose                     n bool      - True to print outputs such as shape of tensors
        # layers                      n list      - contains the neural architecture of the network
        #______________________________________________________________
        # VARIABLES
        # l                             int       - layer counter
        # layer                         list      - list of tensors for each layer of the network
        # drop_val                      tensor    - keep value for dropout layer (set to 1 for output layer)
        #______________________________________________________________
        if n.verbose: print(input_tensor)
        layer = [input_tensor]
        for l in range(1, len(n.layers)):
            if l < len(n.layers) - 1:
                drop_val = dropout
            else:
                drop_val = 1.
            if type(n.layers[l]) == list:
                with tf.variable_scope('layer_' + str(l)):
                    layer.append(n.conv(layer[-1], l, drop_val))
            else:
                if len(layer[-1].get_shape()) > 2:
                    layer.append(tf.reshape(layer[-1], (-1, np.prod(layer[-1].get_shape()[1:]))))
                with tf.variable_scope('layer_' + str(l)):
                    layer.append(n.dense(layer[-1], l, drop_val))
            if n.verbose: print(layer[-1])
        return layer[-1]

    def Fisher(n, a, a_m, a_p, dd):
        # CALCULATE THE FISHER INFORMATION
        #______________________________________________________________
        # CALLED FROM (DEFINED IN IMNN.py)
        # setup(optional func)                    - builds generic or auto built network
        #______________________________________________________________
        # RETURNS
        # tensor
        # Fisher information matrix
        #______________________________________________________________
        # INPUTS
        # a                             tensor    - network output for simulations at fiducial parameter value
        # a_m                           tensor    - network output for simulations below fiducial parameter value
        # a_p                           tensor    - network output for simulations above fiducial parameter value
        # dd                            tensor    - inverse difference between upper and lower parameter value
        # n_s                         n int       - number of simulations in each combination
        # n_summaries                 n int       - number of outputs from the network
        # verbose                     n bool      - True to print outputs such as shape of tensors
        # n_p                         n int       - number of differentiation simulations in each combination
        #______________________________________________________________
        # VARIABLES
        # a_                            tensor    - reshaped network outputs for fiducial simulations
        # μ                           n tensor    - mean of network outputs for fiducial simulations
        # outmm                         tensor    - difference between mean and network outputs for fiducial simulations
        # C                           n tensor    - covariance of network outputs for fiducial simulations
        # iC                          n tensor    - inverse covariance of network outputs for fiducial simulations
        # a_m_                          tensor    - reshaped network outputs for lower parameter simulations
        # a_p_                          tensor    - reshaped network outputs for upper parameter simulations
        # dμdθ                        n tensor    - numerical derivative of the mean of network outputs
        #______________________________________________________________
        a_ = tf.reshape(a, (-1, n.n_s, n.n_summaries), name = 'central_output')
        if n.verbose: print(a_)
        n.μ = tf.reduce_mean(a_, axis = 1, keepdims = True, name = 'central_mean')
        if n.verbose: print(n.μ)
        outmm = tf.subtract(a_, n.μ, name = 'central_difference_from_mean')
        if n.verbose: print(outmm)
        n.C = tf.divide(tf.einsum('ijk,ijl->ikl', outmm, outmm), tf.constant((n.n_s - 1.), dtype = n._FLOATX), name = 'central_covariance')
        if n.verbose: print(n.C)
        n.iC = tf.matrix_inverse(n.C, name = 'central_inverse_covariance')
        if n.verbose: print(n.iC)
        a_m_ = tf.reshape(a_m, (-1, n.n_p, n.n_params, n.n_summaries), name = 'lower_output')
        if n.verbose: print(a_m_)
        a_p_ = tf.reshape(a_p, (-1, n.n_p, n.n_params, n.n_summaries), name = 'upper_output')
        if n.verbose: print(a_p_)
        n.dμdθ = tf.divide(tf.einsum('ijkl,k->ikl', tf.subtract(a_p_, a_m_), dd), tf.constant(n.n_p, dtype = n._FLOATX), name = 'mean_derivative')
        if n.verbose: print(n.dμdθ)
        return tf.einsum('ijk,ilk->ijl', n.dμdθ, tf.einsum('ijk,ilk->ilj', n.iC, n.dμdθ))

    def asymptotic_likelihood(n, output_real):
        # CALCULATE THE ASYMPTOTIC LIKELIHOOD
        #______________________________________________________________
        # CALLED FROM (DEFINED IN IMNN.py)
        # setup(optional func)                    - builds generic or auto built network
        #______________________________________________________________
        # RETURNS
        # tensor
        # Asymptotic likelihood at a range of parameter values
        #______________________________________________________________
        # INPUTS
        # output_real                   tensor    - IMNN summary of real data
        # θ_fid                       n tensor    - fiducial parameter input tensor for calculating MLE
        # prior                       n tensor    - prior range for each parameter for calculating MLE
        # μ                           n tensor    - mean of network outputs for fiducial simulations
        # Ci                          n tensor    - inverse covariance of network outputs for fiducial simulations
        # dμdθ                        n tensor    - numerical derivative of the mean of network outputs
        #______________________________________________________________
        # VARIABLES
        # Δθ                            tensor    - range over which to find the maximum of the likelihood
        # approximate_likelihood        tensor    - approximate likelihood over prior range
        #______________________________________________________________
        Δθ = n.prior - tf.expand_dims(n.θ_fid, 2)
        approximate_likelihood = tf.exp(- 0.5 * (tf.expand_dims(tf.expand_dims(tf.einsum("ij,ij->i", output_real, tf.einsum("ijk,ik->ij", n.iC, output_real)), 1) + tf.einsum("ijk,ik->ij", n.μ, tf.einsum("ijk,ik->ij", n.iC, output_real)) + tf.einsum("ij,ikj->ik", output_real, tf.einsum("ijk,ilk->ilj", n.iC, n.μ)) + tf.einsum("ijk,ijk->ij", n.μ, tf.einsum("ijk,ilk->ilj", n.iC, n.μ)), 2) - tf.einsum("ijk,ij->ijk", Δθ, tf.einsum("ijk,ik->ij", n.dμdθ, tf.einsum("ijk,ik->ij", n.iC, output_real))) - tf.einsum("ijk,ij->ijk", Δθ, tf.einsum("ij,ikj->ik", output_real, tf.einsum("ijk,ilk->ilj", n.iC, n.dμdθ))) + tf.einsum("ijk,ij->ijk", Δθ, tf.einsum("ijk,ijk->ij", n.dμdθ, tf.einsum("ijk,ilk->ilj", n.iC, n.μ))) + tf.einsum("ijk,ij->ijk", Δθ, tf.einsum("ijk,ijk->ij", n.μ, tf.einsum("ijk,ilk->ilj", n.iC, n.dμdθ))) + tf.einsum("ijk,ijk->ijk", Δθ, tf.einsum("ijk,ij->ijk", Δθ, tf.einsum("ijk,ijk->ij", n.dμdθ, tf.einsum("ijk,ilk->ilj", n.iC, n.dμdθ))))))
        return approximate_likelihood / tf.reduce_sum(approximate_likelihood * (n.prior[:, :, 1] - n.prior[:, :, 0]), 2)

    def maximumlikelihoodestimate(n, output_real):
        # CALCULATE THE MAXIMUM LIKELIHOOD ESTIMATE
        #______________________________________________________________
        # CALLED FROM (DEFINED IN IMNN.py)
        # setup(optional func)                    - builds generic or auto built network
        #______________________________________________________________
        # RETURNS
        # tensor
        # Maximum likelihood estimate
        #______________________________________________________________
        # INPUTS
        # output_real                   tensor    - IMNN summary of real data
        # θ_fid                       n tensor    - fiducial parameter input tensor for calculating MLE
        # μ                           n tensor    - mean of network outputs for fiducial simulations
        # Ci                          n tensor    - inverse covariance of network outputs for fiducial simulations
        # dμdθ                        n tensor    - numerical derivative of the mean of network outputs
        #______________________________________________________________
        # VARIABLES
        # iF                            tensor    - inverse Fisher information matrix from fiducial simulations
        #______________________________________________________________
        iF = tf.matrix_inverse(n.F)
        return tf.expand_dims(n.θ_fid, 2) + tf.einsum("ijk,ikl->ijl", iF, tf.einsum("ijk,ilk->ilj", n.iC, tf.einsum("ijk,ijk->ijk", n.dμdθ, tf.expand_dims(output_real, 1) - n.μ)))

    def loss(n, F):
        # CALCULATE THE LOSS FUNCTION
        #______________________________________________________________
        # CALLED FROM (DEFINED IN IMNN.py)
        # setup(optional func)                    - builds generic or auto built network
        #______________________________________________________________
        # RETURNS
        # tensor
        # loss function (-0.5 * |F|^2)
        #______________________________________________________________
        # INPUTS
        # F                           n tensor    - Fisher information matrix
        # _FLOATX                     n tf type   - TensorFlow type
        #______________________________________________________________
        # VARIABLES
        # IFI                           tensor    - determinant of the Fisher information matrix
        #______________________________________________________________
        IFI = tf.matrix_determinant(tf.reduce_sum(F, axis = 0))
        return tf.multiply(tf.constant(-0.5, dtype = n._FLOATX), tf.square(IFI))

    def setup(n, η, network = None):
        # SETS UP GENERIC NETWORK
        #______________________________________________________________
        # FUNCTIONS (DEFINED IN IMNN.py)
        # build_network(tensor, tensor) tensor    - builds predefined network architecture
        # Fisher(tensor, tensor, tensor, tensor)
        #                               tensor    - calculates Fisher information
        # maximumlikelihoodestimate(tensor)
        #                               tensor    - calculates maximum likelihood estimate
        # asymptotic_likelihood(tensor) tensor    - calculates the asymptotic likelihood
        # loss(tensor)                  tensor    - calculates loss function
        # training_scheme(float)        float     - defines the minimisation scheme for backpropagation
        # begin_session()                         - starts interactive tensorflow session and initialises variables
        #______________________________________________________________
        # FUNCTIONS (DEFINED IN utils.py)
        # to_prebuild(func)                       - checks whether network builder is provided
        #______________________________________________________________
        # INPUTS
        # η                             float     - learning rate
        # network              optional func      - externally provided function for building network
        # inputs                      n int/list  - number of inputs (int) or shape of input (list)
        # n_params                    n int       - number of parameters in the model
        # prebuild                    n bool      - True to allow IMNN to build the network
        # verbose                     n bool      - True to print outputs such as shape of tensors
        # get_MLE                     n bool      - True to calculate MLE
        #______________________________________________________________
        # VARIABLES
        # x                           n tensor    - fiducial simulation input tensor
        # x_real                      n tensor    - extra feedforward input tensor for calculating MLE
        # θ_fid                       n tensor    - fiducial parameter input tensor for calculating MLE
        # prior                       n tensor    - prior range for each parameter for calculating MLE
        # x_m                         n tensor    - below fiducial simulation input tensor
        # x_p                         n tensor    - above fiducial simulation input tensor
        # dd                          n tensor    - inverse difference between upper and lower parameter value
        # dropout                     n tensor    - keep rate for dropout layer
        # output                        tensor    - network output for simulations at fiducial parameter value
        # output                      n tensor    - network output for simulations at fiducial parameter value (named)
        # output_m                      tensor    - network output for simulations below fiducial parameter value
        # output_p                      tensor    - network output for simulations above fiducial parameter value
        # output_real                   tensor    - IMNN summary of real data
        # F                           n tensor    - Fisher information matrix
        # MLE                         n tensor    - MLE of parameters
        # AL                          n tensor    - asymptotic likelihood at range of parameter values
        #______________________________________________________________
        n.x = tf.placeholder(n._FLOATX, shape = [None] + n.inputs, name = "x")
        if n.get_MLE:
            n.x_real = tf.placeholder(n._FLOATX, shape = [None] + n.inputs, name = "x_real")
            n.θ_fid = tf.placeholder(dtype = n._FLOATX, shape = [None, n.n_params], name = "fiducial")
            n.prior = tf.placeholder(dtype = n._FLOATX, shape = [None, n.n_params, 1000], name = "prior")
        n.x_m = tf.placeholder(n._FLOATX, shape = [None] + n.inputs, name = "x_m")
        n.x_m = tf.stop_gradient(n.x_m)
        n.x_p = tf.placeholder(n._FLOATX, shape = [None] + n.inputs, name = "x_p")
        n.x_p = tf.stop_gradient(n.x_p)
        n.dd = tf.placeholder(n._FLOATX, shape = (n.n_params), name = "dd")
        n.dropout = tf.placeholder(n._FLOATX, shape = (), name = "dropout")
        if n.prebuild:
            network = n.build_network
        utils.utils().to_prebuild(network)
        with tf.variable_scope("IMNN") as scope:
            output = network(n.x, n.dropout)
        n.output = tf.identity(output, name = "output")
        if n.verbose: print(n.output)
        with tf.variable_scope("IMNN") as scope:
            scope.reuse_variables()
            output_m = network(n.x_m, n.dropout)
            scope.reuse_variables()
            output_p = network(n.x_p, n.dropout)
            if n.get_MLE:
                scope.reuse_variables()
                output_real = tf.identity(network(n.x_real, 1.), name = "output_real")
        n.F = tf.identity(n.Fisher(n.output, output_m, output_p, n.dd), name = 'fisher_information')
        if n.verbose: print(n.F)
        if n.get_MLE:
            n.MLE = tf.identity(n.maximumlikelihoodestimate(output_real), name = "maximum_likelihood_estimate")
            if n.verbose: print(n.MLE)
            n.AL = tf.identity(n.asymptotic_likelihood(output_real), name = "asymptotic_likelihood")
            if n.verbose: print(n.AL)
        n.training_scheme(η)
        n.begin_session()


    def training_scheme(n, η):
        # MINIMISATION SCHEME FOR BACKPROPAGATION
        #______________________________________________________________
        # FUNCTIONS (DEFINED IN IMNN.py)
        # loss(tensor)                  tensor    - calculates loss function
        #______________________________________________________________
        # FUNCTIONS (DEFINED IN utils.py)
        # isfloat(list)                 float     - checks that parameter is a float
        #______________________________________________________________
        # INPUTS
        # η                             float     - learning rate
        # F                           n tensor    - Fisher information matrix
        #______________________________________________________________
        # VARIABLES
        # backpropagate               n tf opt    - minimisation scheme for the network
        #______________________________________________________________
        η = utils.utils().isfloat(η, key = 'η')
        #n.backpropagate = tf.train.AdamOptimizer(η).minimize(n.loss(n.F))
        n.backpropagate = tf.train.GradientDescentOptimizer(η).minimize(n.loss(n.F))

    def shuffle(n, data, data_m, data_p, n_train):
        # SHUFFLES DATA
        #______________________________________________________________
        # CALLED FROM (DEFINED IN IMNN.py)
        # train(list, int, int, float, array, optional list)
        #                                         - trains the network
        #______________________________________________________________
        # RETURNS
        # array, array, array
        #______________________________________________________________
        # INPUTS
        # data                          array     - data at fiducial parameter value
        # data_m                        array     - data below fiducial parameter value
        # data_p                        array     - data above fiducial parameter value
        # n_train                       int       - number of combinations to split training set into
# NEED TO CHECK MULTIPLE PARAMS # n_params                    n int       - number of parameters in the model
        # n_s                         n int       - number of simulations in each combination
        # n_p                         n int       - number of differentiation simulations in each combination
        #______________________________________________________________
        # VARIABLE
        # full_shuffle                  array     - indices of simulations
        # d                             array     - shuffled data
        # partial_shuffle               array     - indices of derivative simulations
        # d_m                           array     - shuffled lower fiducial parameter data
        # d_p                           array     - shuffled upper fiducial parameter data
        #______________________________________________________________
        full_shuffle = np.arange(n.n_s * n_train)
        np.random.shuffle(full_shuffle)
        full_shuffle = full_shuffle.reshape(n_train, n.n_s)
        d = np.array([data[full_shuffle[i]] for i in range(n_train)])
        partial_shuffle = np.arange(n.n_p * n_train)
        np.random.shuffle(partial_shuffle)
        partial_shuffle = partial_shuffle.reshape(n_train, n.n_p)
        d_m = np.array([data_m[partial_shuffle[i]] for i in range(n_train)])
        d_p = np.array([data_p[partial_shuffle[i]] for i in range(n_train)])
        return d, d_m, d_p

    def get_combination_data(n, data, combination, n_batches):
        # GETS SINGLE COMBINATION OF DATA
        #______________________________________________________________
        # CALLED FROM (DEFINED IN IMNN.py)
        # train(list, int, int, float, array, optional list)
        #                                         - trains the network
        #______________________________________________________________
        # RETURNS
        # array, array, array
        #______________________________________________________________
        # INPUTS
        # data                          list      - data at fiducial, lower and upper parameter values
        # combinations                  int       - combination counter
        # n_batches                     int       - number of batches to process at once
        #______________________________________________________________
        # VARIABLE
        # td_                           array     - single combination of data at fiducial parameter value
        # t                             array     - reshaped single combination of data at fiducial parameter value
        # t_m__                         array     - single combination of data below fiducial parameter value
        # t_m_                          array     - reshaped single combination of data below fiducial parameter value
        # t_m                           array     - more reshaped single combination of data below fiducial parameter value
        # t_p__                         array     - single combination of data above fiducial parameter value
        # t_p_                          array     - reshaped single combination of data above fiducial parameter value
        # t_p                           array     - more reshaped single combination of data above fiducial parameter value
        #______________________________________________________________
        td_ = data[0][combination * n_batches: (combination + 1) * n_batches]
        t = td_.reshape([np.prod(td_.shape[: 2])] + list(td_.shape[2:]))
        t_m__ = data[1][combination * n_batches: (combination + 1) * n_batches]
        t_m_ = t_m__.reshape([np.prod(t_m__.shape[:2])] + list(t_m__.shape[2:]))
        t_m = t_m_.reshape([np.prod(t_m_.shape[:2])] + list(t_m_.shape[2:]))
        t_p__ = data[2][combination * n_batches: (combination + 1) * n_batches]
        t_p_ = t_p__.reshape([np.prod(t_p__.shape[:2])] + list(t_p__.shape[2:]))
        t_p = t_p_.reshape([np.prod(t_p_.shape[:2])] + list(t_p_.shape[2:]))
        return t, t_m, t_p

    def train(n, train_data, num_epochs, n_train, num_batches, keep_rate, der_den, test_data = None):
        # TRAIN INFORMATION MAXIMISING NEURAL NETWORK
        #______________________________________________________________
        # RETURNS
        # list or list, list
        # determinant of Fisher information matrix at the end of each epoch for train data (and test data)
        #______________________________________________________________
        # FUNCTIONS (DEFINED IN IMNN.py)
        # shuffle(array, array, array)  array     - shuffles the simulations on each epoch
        # get_combination_data(list, int, int)
        #                               array, array, array
        #                                         - gets individual combination of data
        # save_network(optional Bool)             - saves the network (if n.save_file is not None)
        #______________________________________________________________
        # FUNCTIONS (DEFINED IN utils.py)
        # check_data(class, list, int, optional bool)
        #                               bool      - checks whether data is of correct format (and whether to use test data)
        # positive_integer(list)        int       - checks that parameter is a positive integer
        # enough(int, int, optional bool, optional bool)
        #                                         - checks number of batches is less than n_train and makes use of all data
        # constrained_float(float, string)
        #                               float     - checks the dropout is between 0 and 1
        #______________________________________________________________
        # INPUTS
        # train_data                    list      - data at fiducial, lower and upper parameter values
        # num_epochs                    int       - number of epochs to train
        # n_train                       int       - number of combinations to split training set into
        # num_batches                   int       - number of batches to process at once
        # keep_rate                     float     - keep rate for dropout
        # der_den                       array     - inverse difference between upper and lower parameter values
        # test_data            optional list      - data at fiducial, lower and upper parameter values for testing
        # sess                        n session   - interactive tensorflow session (with initialised parameters)
        # backpropagate               n tf opt    - minimisation scheme for the network
        # x                           n tensor    - fiducial simulation input tensor
        # x_m                         n tensor    - below fiducial simulation input tensor
        # x_p                         n tensor    - above fiducial simulation input tensor
        # dropout                     n tensor    - keep rate for dropout layer
        # dd                          n tensor    - inverse difference between upper and lower parameter value
        # F                           n tensor    - Fisher information matrix
        #______________________________________________________________
        # VARIABLES
        # do_test                       bool      - True if using test_data
        # train_F                       list      - determinant Fisher information matrix at end of train epoch
        # test_F                        list      - determinant Fisher information matrix of test data at end of epoch
        # epoch                         int       - epoch counter
        # td                            list      - shuffled data at fiducial, lower and upper parameter values
        # t                             array     - reshaped single combination of data at fiducial parameter value
        # t_m                           array     - more reshaped single combination of data below fiducial parameter value
        # t_p                           array     - more reshaped single combination of data above fiducial parameter value
        #______________________________________________________________
        utils.utils().check_data(n, train_data, n_train)
        do_test = utils.utils().check_data(n, test_data, 1, test = True)
        num_epochs = utils.utils().positive_integer(num_epochs, key = 'number of epochs')
        n_train = utils.utils().positive_integer(n_train, key = 'number of combinations')
        num_batches = utils.utils().positive_integer(num_batches, key = 'number of batches')
        utils.utils().enough(n_train, num_batches, modulus = True)
        keep_rate = utils.utils().constrained_float(keep_rate, key = 'dropout')
        train_F = []
        if do_test:
            test_F = []
            ttd = n.shuffle(test_data[0], test_data[1], test_data[2], 1)
            tt, tt_m, tt_p = n.get_combination_data(ttd, 0, 1)
        tq = tqdm.trange(num_epochs)
        for epoch in tq:

            td = n.shuffle(train_data[0], train_data[1], train_data[2], n_train)
            for combination in range(n_train):
                t, t_m, t_p = n.get_combination_data(td, combination, num_batches)
                n.sess.run(n.backpropagate, feed_dict = {n.x: t, n.x_m: t_m, n.x_p: t_p, n.dropout: keep_rate, n.dd: der_den})
            train_F.append(np.linalg.det(n.sess.run(n.F, feed_dict = {n.x: t, n.x_m: t_m, n.x_p: t_p, n.dropout: 1., n.dd: der_den})))
            if do_test:
                test_F.append(np.linalg.det(n.sess.run(n.F, feed_dict = {n.x: tt, n.x_m: tt_m, n.x_p: tt_p, n.dropout: 1., n.dd: der_den})))
                tq.set_postfix(detF = train_F[-1][-1], detF_test = test_F[-1][-1])
            else:
                tq.set_postfix(detF = train_F[-1][-1])
        if n.save_file is not None:
            n.save_network()
        if do_test:
            return train_F, test_F
        else:
            return train_F

    def ABC(n, real_data, estimation_simulations, der_den, prior, draws, generate_simulation, at_once = True):
        # PERFORM APPROXIMATE BAYESIAN COMPUTATION WITH RANDOM DRAWS FROM PRIOR
        #______________________________________________________________
        # CALLED FROM
        # PMC(array, array, list, int, int, func, float, optional bool, optional list)
        #                               array, float, array, array, array, int
        #                                         - performs population monte carlo
        #______________________________________________________________
        # RETURNS
        # array, float, array, array, array
        # sampled parameter values, network summary of real data, summaries of simulations,
        #     distances between simulation summaries, real summary and Fisher information
        #______________________________________________________________
        # INPUTS
        # real_data                     array     - real data to be summarised
        # estimation_simulations        list      - list of central, lower and upper simulations to calculate Fisher information
        # der_den                       array     - denominator to calculate the numerical derivative
        # prior                         list      - lower and upper bound of uniform prior
        # draws                         int       - number of draws from the prior
        # generate_simulation           func      - function which generates the simulation at parameter value
        # at_once              optional bool      - True if generate all simulations and calculate all summaries at once
        # sess                        n session   - interactive tensorflow session (with initialised parameters)
        # output                      n tensor    - network output for simulations at fiducial parameter value
        # x                           n tensor    - fiducial simulation input tensor
        # dropout                     n tensor    - keep rate for dropout layer
        #______________________________________________________________
        # VARIABLES
        # F                             array     - Fisher information matrix of a group of simulations
        # summary                       float     - summary of the real data
        # θ                             array     - all draws from prior
        # simulations                   array     - generated simulations at all parameter draws
        # simulation_summaries          float     - summaries of each of the generated simulations
        # theta                         int       - counter for number of draws
        # simulation                    array     - generated simulation at indivdual parameter draw
        # difference                    array     - difference between summary of real data and summaries of simulations
        # distance                      array     - Euclidean distance between real summary and summaries of simulations
        #______________________________________________________________
        F = n.sess.run(n.F, feed_dict = {n.x: estimation_simulations[0], n.x_m: estimation_simulations[1], n.x_p: estimation_simulations[2], n.dropout: 1., n.dd: der_den})[0]
        summary = n.sess.run(n.output, feed_dict = {n.x: real_data, n.dropout: 1.})[0]
        θ = np.random.uniform(prior[0], prior[1], draws)
        if at_once:
            simulations = generate_simulation(θ)
            simulation_summaries = n.sess.run(n.output, feed_dict = {n.x: simulations, n.dropout: 1.})
        else:
            simulation_summaries = np.zeros([draws, n.n_summaries])
            for theta in tqdm.tqdm(range(draws)):
                simulation = generate_simulation([θ[theta]])
                simulation_summaries[theta] = n.sess.run(n.output, feed_dict = {n.x: simulation, n.dropout: 1.})[0]
        difference = simulation_summaries - summary
        distances = np.sqrt(np.einsum('ij,ij->i', difference, np.einsum('jk,ik->ij', F, difference)))
        return θ, summary, simulation_summaries, distances, F

    def PMC(n, real_data, estimation_simulations, der_den, prior, num_draws, num_keep, generate_simulation, criterion, at_once = True, samples = None):
        # PERFORM APPROXIMATE BAYESIAN COMPUTATION USING POPULATION MONTE CARLO
        #______________________________________________________________
        # RETURNS
        # array, float, array, array, array, int
        # sampled parameter values, network summary of real data, distances between simulation summaries and real summary,
        #    summaries of simulations, weighting of samples, total number of draws so far
        #______________________________________________________________
        # FUNCTIONS (DEFINED IN utils.py)
        # to_continue(list)             bool      - True if continue running PMC
        # enough(float/int, float/int, optional bool, optional bool)
        #                                         - checks that first value is higher than second
        #______________________________________________________________
        # INPUTS
        # real_data                     array     - real data to be summarised
        # estimation_simulations        list      - list of central, lower and upper simulations to calculate Fisher information
        # der_den                       array     - denominator to calculate the numerical derivative
        # prior                         list      - lower and upper bound of uniform prior
        # num_draws                     int       - number of initial draws from the prior
        # num_keep                      int       - number of samples in the approximate posterior
        # generate_simulation           func      - function which generates the simulation at parameter value
        # criterion                     float     - ratio of number of draws wanted over number of draws needed
        # at_once              optional bool      - True if generate all simulations and calculate all summaries at once
        # samples              optional list      - list of all the outputs of PMC to continue running PMC
        # sess                        n session   - interactive tensorflow session (with initialised parameters)
        # output                      n tensor    - network output for simulations at fiducial parameter value
        # x                           n tensor    - fiducial simulation input tensor
        # dropout                     n tensor    - keep rate for dropout layer
        #______________________________________________________________
        # VARIABLES
        # continue_from_samples         bool      - True is continue running the PMC
        # θ_                            array     - parameter draws from approximate posterior
        # summary                       float     - summary of the real data
        # ρ_                            array     - distance between real summary and summaries from approximate posterior
        # s_                            array     - summaries from approximate posterior
        # W                             array     - weighting for samples in approximate posterior
        # total_draws                   int       - total number of draws from the prior so far
        # θ                             array     - all parameter draws from prior
        # s                             float     - summaries of each of the generated simulations from prior
        # ρ                             array     - distance between real summary and summaries of simulations from prior
        # F                             array     - Fisher information matrix of a group of simulations
        # pθ                            float     - value of prior at given θ value (for uniform prior)
        # iteration                     int       - counter for number of iterations of PMC
        # criterion_reached             float     - number of draws wanted over number of current draws
        # cov                           array     - weighted covariance of drawn samples
        # W_temp                        array     - copy of sample weighting array for updating
        # ϵ                             float     - current accept distance
        # redraw_index                  array     - indices of parameter draws to redraw
        # current_draws                 int       - number of parameters being updated at once
        # draws                         int       - counter for number of draws per iteration
        # θ_temp                        array     - proposed updated parameter sample values
        # below_prior                   array     - indices of parameter values below prior
        # above_prior                   array     - indices of parameter values above prior
        # simulations                   array     - generated simulations at all parameter draws
        # simulation_summaries          float     - summaries of each of the generated simulations
        # theta                         int       - counter for number of draws
        # simulation                    array     - generated simulation at indivdual parameter draw
        # difference                    array     - difference between summary of real data and summaries of simulations
        # ρ_temp                        array     - distance between real and simulated summaries for proposed draws
        # accept_index                  array     - indices of proposed parameter values to keep
        #______________________________________________________________
        continue_from_samples = utils.utils().to_continue(samples)
        utils.utils().enough(num_draws, num_keep)
        if continue_from_samples:
            θ_ = samples[0]
            summary = samples[1]
            ρ_ = samples[2]
            s_ = samples[3]
            W = samples[4]
            total_draws = samples[5]
            F = samples[6]
        else:
            θ, summary, s, ρ, F = n.ABC(real_data, estimation_simulations, der_den, prior, num_draws, generate_simulation, at_once)
            keep_index = np.argsort(np.abs(ρ))
            θ_ = θ[keep_index[: num_keep]]
            ρ_ = ρ[keep_index[: num_keep]]
            s_ = s[keep_index[: num_keep]]
            W = np.ones(num_keep) / num_keep
            total_draws = num_draws
        pθ = 1./(prior[1] - prior[0])
        iteration = 0
        criterion_reached = 1e10
        while criterion < criterion_reached:
            cov = np.cov(θ_, aweights = W)
            ϵ = np.percentile(ρ_, 75)
            redraw_index = np.where(ρ_ >= ϵ)[0]
            W_temp = np.copy(W)
            current_draws = len(redraw_index)
            draws = 0
            while current_draws > 0:
                draws += current_draws
                θ_temp = np.random.normal(θ_[redraw_index], np.sqrt(cov))
                below_prior = np.where(θ_temp <= prior[0])[0]
                above_prior = np.where(θ_temp > prior[1])[0]
                while len(below_prior) > 0 or len(above_prior) > 0:
                    θ_temp[below_prior] = np.random.normal(θ_[redraw_index[below_prior]], np.sqrt(cov))
                    θ_temp[above_prior] = np.random.normal(θ_[redraw_index[above_prior]], np.sqrt(cov))
                    below_prior = np.where(θ_temp <= prior[0])[0]
                    above_prior = np.where(θ_temp > prior[1])[0]
                if at_once:
                    simulations = generate_simulation(θ_temp)
                    simulation_summaries = n.sess.run(n.output, feed_dict = {n.x: simulations, n.dropout: 1.})
                else:
                    simulation_summaries = np.zeros([current_draws, n.n_summaries])
                    for theta in range(current_draws):
                        simulation = generate_simulation([θ_temp[theta]])
                        simulation_summaries[theta] = n.sess.run(n.output, feed_dict = {n.x: simulation, n.dropout: 1.})[0]
                difference = simulation_summaries - summary
                ρ_temp = np.sqrt(np.einsum('ij,ij->i', difference, np.einsum('jk,ik->ij', F, difference)))
                accept_index = np.where(ρ_temp <= ϵ)[0]
                if len(accept_index) > 0:
                    ρ_[redraw_index[accept_index]] = ρ_temp[accept_index]
                    θ_[redraw_index[accept_index]] = θ_temp[accept_index]
                    s_[redraw_index[accept_index]] = simulation_summaries[accept_index]
                    W_temp[redraw_index[accept_index]] = pθ / np.sum(W[:, None] * np.exp(-0.5 * (np.stack([θ_temp[accept_index] for i in range(num_keep)]) - θ_[:, None])**2. / cov) / np.sqrt(2 * np.pi * cov), axis = 0)
                redraw_index = np.where(ρ_ >= ϵ)[0]
                current_draws = len(redraw_index)
            W = np.copy(W_temp)
            criterion_reached = num_keep / draws
            iteration += 1
            total_draws += draws
            print('iteration = ' + str(iteration) + ', current criterion = ' + str(criterion_reached) + ', total draws = ' + str(total_draws) + ', ϵ = ' + str(ϵ) + '.', end = '\r')
        return θ_, summary, ρ_, s_, W, total_draws, F
