#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>

#define NUM_THREADS 2

pthread_mutex_t mutex1 = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t mutex2 = PTHREAD_MUTEX_INITIALIZER;

void* thread_func(void* arg) {
    int id = *(int*)arg;

    if (id == 0) {
        pthread_mutex_lock(&mutex1);
        printf("Thread %d acquired mutex1\n", id);

        // Simulate some work
        sleep(1);

        pthread_mutex_lock(&mutex2);
        printf("Thread %d acquired mutex2\n", id);
    } else {
        pthread_mutex_lock(&mutex2);
        printf("Thread %d acquired mutex2\n", id);

        // Simulate some work
        sleep(1);

        pthread_mutex_lock(&mutex1);
        printf("Thread %d acquired mutex1\n", id);
    }

    pthread_mutex_unlock(&mutex1);
    pthread_mutex_unlock(&mutex2);

    return NULL;
}

int main() {
    pthread_t threads[NUM_THREADS];
    int thread_ids[NUM_THREADS] = {0, 1};

    for (int i = 0; i < NUM_THREADS; i++) {
        if (pthread_create(&threads[i], NULL, thread_func, &thread_ids[i]) != 0) {
            perror("Failed to create thread");
            exit(EXIT_FAILURE);
        }
    }

    for (int i = 0; i < NUM_THREADS; i++) {
        pthread_join(threads[i], NULL);
    }

    return 0;
}