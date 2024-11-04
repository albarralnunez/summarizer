# Mini summarizer.AI

A starting point for dockerized python web

## Development

### Prerequisites
 - Docker
 - Docker Compose
 - Node.js


### Initialize data set

 - `./init-data.sh`

### Frontend

 - `cd frontend`
 - `npm i`
 - `npm run dev`

### Run Server on host

 - `uvicorn server.main:app --reload`

### Docker

 - `./dc build`
 - `./dc up`

To update docker python libraries, add them to environment.yml. Note `./dc` is a convience alias for `docker compose`.

## TF-IDF Implementation with Concurrency and Parallelization Optimizations

This project uses TF-IDF (Term Frequency-Inverse Document Frequency) for text summarization, with several optimizations for handling large files and improving performance.

### How it works

1. **Term Frequency (TF)**: Measures how often a term appears in a document.
2. **Inverse Document Frequency (IDF)**: Measures the importance of a term across all documents.
3. **TF-IDF**: The product of TF and IDF, indicating the overall importance of a term.

### Implementation Details

The TF-IDF implementation can be found in the [`summarize_text`](server/main.py#L92) function, which includes the following optimizations:

1. **Asynchronous Processing**: The function uses `async/await` to handle I/O operations efficiently.

2. **Batched Processing**: Sentences are processed in batches to reduce memory usage and improve performance.

3. **Parallel Word Indexing**: A `ProcessPoolExecutor` is used to parallelize the creation of word indices across multiple CPU cores.

4. **Sparse Matrix Representation**: The `scipy.sparse.csr_matrix` is used to efficiently store and manipulate the word count matrix, reducing memory usage for large documents.

5. **Incremental TF-IDF Calculation**: The TF-IDF matrix is built incrementally as batches of sentences are processed, allowing for efficient handling of large documents.

6. **Early Termination**: 
   ```python
   if len(sentences) >= 2 * num_sentences:
       break
   ```
   The processing stops after analyzing a sufficient number of sentences, preventing unnecessary computation for very large documents.

   Early termination is both possible and advised for several reasons:

   - **Diminishing Returns**: Most important information tends to be concentrated at the beginning or spread throughout the text. After processing twice the number of requested summary sentences, the likelihood of finding significantly more important sentences diminishes.
   
   - **Performance Optimization**: For very large documents, processing the entire text can be time-consuming. Early termination provides a meaningful summary much faster, especially for real-time applications.
   
   - **Relevance to Summary Length**: If a summary of N sentences is requested, processing 2N sentences is often sufficient to identify the most important ones, balancing thoroughness with efficiency.
   
   - **Adaptability**: The early termination threshold can be easily adjusted based on specific needs or document characteristics.
   
   - **Memory Efficiency**: By limiting the number of processed sentences, the system maintains a smaller working set in memory, beneficial for very large documents.
   
   - **Consistent Performance**: Early termination helps maintain more consistent performance across documents of varying lengths.

   Note: While generally beneficial, early termination may not suit all use cases, such as documents with critical information heavily skewed towards the end or applications requiring exhaustive analysis.

### Key Optimizations

1. **Asynchronous File Reading**: This function reads the file or text input asynchronously, yielding sentences as they become available.   
    ```python
   async def process_input(file: Optional[UploadFile], text: Optional[str]) -> AsyncIterator[str]:   
    ```


2. **Parallel Sentence Processing**: This code uses a `ProcessPoolExecutor` to process sentences in parallel across multiple CPU cores.
    ```python
   async def process_sentences(batch):
       loop = asyncio.get_running_loop()
       with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
           futures = [loop.run_in_executor(executor, process_sentence, sentence, word_to_index) for sentence in batch]
           return await asyncio.gather(*futures)   
    ```
   

3. **Batched Processing**: Sentences are processed in batches to balance memory usage and performance.  
    ```python
   batch_size = max(100, 2 * num_sentences) 
     ```
   

4. **Sparse Matrix Operations**: Sparse matrices are used to efficiently handle large documents with minimal memory usage.  
    ```python
   word_count_matrix = vstack(sentence_vectors)
   tfidf_matrix = tfidf_transformer.fit_transform(word_count_matrix)  
    ```
   

### Benefits

- Efficient processing of large documents
- Reduced memory usage through sparse matrix representations
- Improved performance through parallel processing
- Scalable to various document sizes
- Language-independent approach

For more details, see the [`server/main.py`](server/main.py) file.

# Notes:

I initially created two repositories but had to remove the first one due to an error—I accidentally added the frontend as a submodule and only noticed it later. To resolve this quickly, I re-uploaded the repository.

The initial version featured a custom algorithm. After a short break for personal matters, I created a second version using Sumy.

During cleanup, I kept the client and server simple, as adding complex patterns or excessive splitting didn’t seem necessary. The Python components are likely the most thoroughly documented.

The next day, I had some new ideas I wanted to implement for fun, including significant performance optimizations, client design enhancements, and improvements in code quality and developer experience.


For the first commit it took ~45m, the first optimization +~15m. From there I just started doing some stuff now and then when I had time becuse I liked the challangeThe initial commit took about 45 minutes, with the first optimization adding around 15 more. After that, I continued making improvements here and there when I had time, simply because I enjoyed the challenge.