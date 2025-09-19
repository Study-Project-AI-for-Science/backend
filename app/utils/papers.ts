export const paperData = [
  {
    id: "019960c2-e0fb-73a9-8279-f1a914b6a5b7",
    title: "Attention Is All You Need",
    abstract:
      "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1aa4f1ac167",
    title: "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
    abstract:
      "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1ab7f6d3339",
    title: "Generative Adversarial Networks",
    abstract:
      "We propose a new framework for estimating generative models via an adversarial process, in which we simultaneously train two models: a generative model G that captures the data distribution, and a discriminative model D that estimates the probability that a sample came from the training data rather than G.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1acec752306",
    title: "Deep Residual Learning for Image Recognition",
    abstract:
      "Deeper neural networks are more difficult to train. We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously. We explicitly reformulate the layers as learning residual functions with reference to the layer inputs, instead of learning unreferenced functions.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1adae9e7a9a",
    title: "Language Models are Few-Shot Learners",
    abstract:
      "Recent work has demonstrated substantial gains on many NLP tasks and benchmarks by pre-training on a large corpus of text followed by fine-tuning on a specific task. While typically task-agnostic in architecture, this method still requires task-specific fine-tuning datasets of thousands or tens of thousands of examples.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1aee4eae0a3",
    title: "An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale",
    abstract:
      "While the Transformer architecture has become the de-facto standard for natural language processing tasks, its applications to computer vision remain limited. In vision, attention is either applied in conjunction with convolutional networks, or used to replace certain components of convolutional networks while keeping their overall structure in place.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1af60f8146f",
    title: "DALL·E 2: Hierarchical Text-Conditional Image Generation",
    abstract:
      "We present a hierarchical approach for text-conditional image generation that generates images using a two-stage process: first generating a low-resolution image based on the input text, then upsampling it to a high-resolution image. This approach allows for more coherent and detailed image generation compared to single-stage methods.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1b0f70aa8e7",
    title: "The Lottery Ticket Hypothesis: Finding Sparse, Trainable Neural Networks",
    abstract:
      "Neural network pruning techniques can reduce the parameter counts of trained networks by over 90%, decreasing storage requirements and improving computational performance of inference without compromising accuracy. We propose the lottery ticket hypothesis: dense, randomly-initialized, feed-forward networks contain subnetworks that achieve comparable accuracy to the original network when trained in isolation.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1b10c45e748",
    title: "Contrastive Learning of Visual Representations",
    abstract:
      "Unsupervised visual representation learning has proven to be very effective in learning useful representations without human annotation. In this work, we propose a simple framework for contrastive learning of visual representations called SimCLR. Our framework learns representations by maximizing agreement between differently augmented views of the same data example via a contrastive loss in the latent space.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1b27b6a927c",
    title: "You Only Look Once: Unified, Real-Time Object Detection",
    abstract:
      "We present YOLO, a new approach to object detection. Prior work on object detection repurposes classifiers to perform detection. Instead, we frame object detection as a regression problem to spatially separated bounding boxes and associated class probabilities. A single neural network predicts bounding boxes and class probabilities directly from full images in one evaluation.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1b3d8c5b2a1",
    title: "Neural Architecture Search with Reinforcement Learning",
    abstract:
      "Designing neural network architectures requires significant expertise and human effort. We propose a novel framework that uses reinforcement learning to automatically search for optimal neural architectures. Our method uses a recurrent network as the controller to generate network architectures, which are then evaluated on a separate child network to obtain accuracy metrics.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1b4e7f3c4d2",
    title: "Federated Learning: Collaborative Machine Learning without Centralized Training Data",
    abstract:
      "Machine learning typically requires centralized data collection, which raises privacy concerns. We introduce federated learning, a decentralized approach where multiple clients collaboratively train a shared model without exchanging their local data. Each client trains the model locally and only shares model updates with a central server.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1b5f6a2b3e5",
    title: "Self-Supervised Learning of Visual Features by Contrasting Cluster Assignments",
    abstract:
      "Self-supervised learning has shown great potential in learning useful representations without human annotations. We propose a novel approach called SwAV that learns by comparing cluster assignments of different augmentations of the same image. This method achieves state-of-the-art performance on various downstream tasks while being computationally efficient.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1b6g8d4e6f7",
    title: "EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks",
    abstract:
      "Convolutional neural network scaling has been extensively studied, but the relationship between different dimensions of scaling is often overlooked. We propose a novel scaling method that uniformly scales network width, depth, and resolution with a compound coefficient. This approach achieves better performance and efficiency compared to traditional scaling methods.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1b7h9c5f8g9",
    title: "GPT-3: Language Models are Few-Shot Learners",
    abstract:
      "Scaling language models greatly improves task-agnostic, few-shot performance, sometimes even reaching competitiveness with prior state-of-the-art fine-tuning approaches. We present GPT-3, a 175 billion parameter autoregressive language model that achieves strong performance on many NLP tasks without fine-tuning.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1b8i0b6g1h2",
    title: "Diffusion Models Beat GANs on Image Synthesis",
    abstract:
      "Generative adversarial networks have dominated image synthesis for the past few years, but they suffer from training instability and mode collapse. We show that diffusion models, which learn to reverse a gradual noising process, can generate higher quality images than GANs while being more stable to train.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1b9j1a7h3i4",
    title: "Vision Transformer (ViT): An Image is Worth 16x16 Words",
    abstract:
      "While transformers have become the de-facto standard for natural language processing, their application to computer vision has been limited. We show that a pure transformer applied directly to sequences of image patches can perform very well on image classification tasks, achieving excellent results when pre-trained on large datasets.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1c0k2z8i5j6",
    title: "CLIP: Connecting Text and Images",
    abstract:
      "We present a simple approach for learning joint representations of text and images by training on large datasets of image-text pairs. Our model, CLIP, learns to predict which text snippets are paired with which images. This enables zero-shot transfer to many computer vision tasks without fine-tuning.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1c1l3y9j7k8",
    title: "Stable Diffusion: High-Resolution Image Synthesis with Latent Diffusion Models",
    abstract:
      "Diffusion models have recently achieved state-of-the-art results in image synthesis, but they are computationally expensive. We present Stable Diffusion, which operates in a compressed latent space of a pretrained autoencoder. This approach enables high-resolution image synthesis with significantly reduced computational requirements.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1c2m4x0k9l0",
    title: "Swin Transformer: Hierarchical Vision Transformer using Shifted Windows",
    abstract:
      "Transformers have shown great potential in computer vision, but they lack some inductive biases inherent to CNNs. We propose Swin Transformer, which introduces a hierarchical structure and shifted window mechanism. This design enables the model to process images at multiple scales while maintaining computational efficiency.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1c3n5w1l1m2",
    title: "Segment Anything Model (SAM): A Foundation Model for Image Segmentation",
    abstract:
      "We introduce SAM, a foundation model for image segmentation that can segment any object in any image with a single prompt. The model is trained on a massive dataset of images and masks, enabling zero-shot transfer to new segmentation tasks. SAM represents a significant advance in general-purpose image segmentation.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1c4o6v2m3n4",
    title: "LLaMA: Open and Efficient Foundation Language Models",
    abstract:
      "Large language models have shown remarkable capabilities, but their development has been limited to a few organizations. We present LLaMA, a collection of foundation language models ranging from 7B to 65B parameters. These models achieve competitive performance with existing models while being more efficient and accessible.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1c5p7u3n5o6",
    title: "DINOv2: Learning Robust Visual Features without Supervision",
    abstract:
      "Self-supervised learning has become crucial for learning visual representations, but existing methods often rely on specific augmentations or architectures. We present DINOv2, which learns robust visual features through self-distillation with no labels. The resulting features are highly transferable to downstream tasks.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1c6q8t4o7p8",
    title: "PaLM: Scaling Language Modeling with Pathways",
    abstract:
      "Large language models have shown impressive capabilities across many tasks, but scaling them effectively remains challenging. We present PaLM, a 540 billion parameter language model trained using Pathways, a new ML system. PaLM achieves state-of-the-art performance on various benchmarks while demonstrating strong few-shot learning abilities.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1c7r9s5p9q0",
    title: "Florence: A New Foundation Model for Computer Vision",
    abstract:
      "Foundation models have revolutionized natural language processing, but computer vision still relies on task-specific models. We introduce Florence, a foundation model that unifies a variety of computer vision tasks including captioning, visual question answering, and object detection through a sequence-to-sequence approach.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1c8s0r6q1r2",
    title: "Mixtral: Mixture of Experts for Efficient Language Modeling",
    abstract:
      "Large language models require enormous computational resources, limiting their accessibility. We present Mixtral, a sparse mixture of experts model that achieves strong performance with significantly fewer active parameters. This approach provides a better trade-off between performance and computational efficiency.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1c9t1q7r3s4",
    title: "Croissant: A Model for Understanding Images and Text Together",
    abstract:
      "Multimodal learning has become increasingly important, but existing approaches often treat different modalities separately. We introduce Croissant, a unified model that processes images and text through a shared transformer architecture. This enables seamless integration of visual and textual information for various downstream tasks.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1d0u2p8s5t6",
    title: "Gemini 1.0: A Family of Multimodal Large Language Models",
    abstract:
      "We present Gemini 1.0, a family of multimodal large language models that can process and reason about multiple modalities including text, images, and potentially other data types. These models demonstrate strong capabilities across a wide range of multimodal tasks while maintaining the flexibility of language models.",
  },
  {
    id: "019960c2-e0fb-73a9-8279-f1d1v3o9t7u8",
    title: "Grok: An AI Built for Understanding the Universe",
    abstract:
      "We introduce Grok, an AI assistant designed to be maximally truthful and helpful. Built on advanced transformer architectures, Grok demonstrates strong reasoning capabilities across scientific, mathematical, and general knowledge domains. The model emphasizes safety, accuracy, and beneficial outcomes in all interactions.",
  },
]
