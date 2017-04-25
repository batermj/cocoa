def add_data_generator_arguments(parser):
    from preprocess import add_preprocess_arguments
    from src.basic.scenario_db import add_scenario_arguments
    from src.basic.dataset import add_dataset_arguments

    add_scenario_arguments(parser)
    add_preprocess_arguments(parser)
    add_dataset_arguments(parser)

def get_data_generator(args, model_args, mappings, schema):
    from preprocess import DataGenerator, Preprocessor
    from src.basic.scenario_db import ScenarioDB
    from src.basic.negotiation.price_tracker import PriceTracker
    from src.basic.dataset import read_dataset
    from src.basic.util import read_json
    import time

    scenario_db = ScenarioDB.from_dict(schema, read_json(args.scenarios_path))
    dataset = read_dataset(scenario_db, args)
    lexicon = PriceTracker()

    # Dataset
    preprocessor = Preprocessor(schema, lexicon, model_args.entity_encoding_form, model_args.entity_decoding_form, model_args.entity_target_form)
    if args.test:
        model_args.dropout = 0
        data_generator = DataGenerator(None, None, dataset.test_examples, preprocessor, schema, mappings)
    else:
        data_generator = DataGenerator(dataset.train_examples, dataset.test_examples, None, preprocessor, schema, mappings)

    return data_generator

def add_model_arguments(parser):
    from src.model.encdec import add_basic_model_arguments

    add_basic_model_arguments(parser)

# TODO: factor this
def build_model(schema, mappings, args):
    import tensorflow as tf
    from src.model.word_embedder import WordEmbedder
    from src.model.encdec import BasicEncoder, BasicDecoder, Sampler
    from encdec import BasicEncoderDecoder
    from preprocess import markers

    tf.reset_default_graph()
    tf.set_random_seed(args.random_seed)

    vocab = mappings['vocab']
    pad = vocab.to_ind(markers.PAD)
    with tf.variable_scope('EncoderWordEmbedder'):
        encoder_word_embedder = WordEmbedder(vocab.size, args.word_embed_size, pad)
    with tf.variable_scope('DecoderWordEmbedder'):
        decoder_word_embedder = WordEmbedder(vocab.size, args.word_embed_size, pad)

    if args.decoding[0] == 'sample':
        sample_t = float(args.decoding[1])
        sampler = Sampler(sample_t)
    else:
        raise('Unknown decoding method')

    re_encode = args.re_encode

    if args.model == 'encdec':
        encoder = BasicEncoder(args.rnn_size, args.rnn_type, args.num_layers, args.dropout)
        decoder = BasicDecoder(args.rnn_size, vocab.size, args.rnn_type, args.num_layers, args.dropout, sampler)
        model = BasicEncoderDecoder(encoder_word_embedder, decoder_word_embedder, encoder, decoder, pad, re_encode=re_encode)
    else:
        raise ValueError('Unknown model')
    return model

