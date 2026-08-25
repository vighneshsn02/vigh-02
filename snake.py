import curses
import time
import random

def main(stdscr):
    # Initialize the screen
    stdscr.clear()
    curses.curs_set(0)  # Hide the cursor
    sh, sw = stdscr.getmaxyx()  # Get the screen size

    # Define colors
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)

    # Snake initial position and direction
    snake = [[sh // 2, sw // 2]]
    direction = 'RIGHT'

    # Food position
    food = [random.randint(1, sh - 2), random.randint(1, sw - 2)]

    while True:
        stdscr.clear()

        # Draw the food
        stdscr.addch(food[0], food[1], '*', curses.color_pair(2))

        # Move the snake
        new_head = list(snake[0])
        if direction == 'UP':
            new_head[0] -= 1
        elif direction == 'DOWN':
            new_head[0] += 1
        elif direction == 'LEFT':
            new_head[1] -= 1
        elif direction == 'RIGHT':
            new_head[1] += 1

        # Check for collisions
        if (new_head in snake or 
            new_head[0] < 1 or new_head[0] >= sh - 1 or 
            new_head[1] < 1 or new_head[1] >= sw - 1):
            break

        # Add the new head to the snake
        snake.insert(0, new_head)

        # Check if the snake has eaten the food
        if snake[0] == food:
            food = [random.randint(1, sh - 2), random.randint(1, sw - 2)]
        else:
            # Remove the tail of the snake
            snake.pop()

        # Draw the snake
        for segment in snake:
            stdscr.addch(segment[0], segment[1], '#', curses.color_pair(1))

        # Refresh the screen
        stdscr.refresh()

        # Get user input
        key = stdscr.getch()
        if key == ord('q'):
            break
        elif key == curses.KEY_UP and direction != 'DOWN':
            direction = 'UP'
        elif key == curses.KEY_DOWN and direction != 'UP':
            direction = 'DOWN'
        elif key == curses.KEY_LEFT and direction != 'RIGHT':
            direction = 'LEFT'
        elif key == curses.KEY_RIGHT and direction != 'LEFT':
            direction = 'RIGHT'

        # Control the game speed
        time.sleep(0.1)

    # Clean up
    curses.curs_set(1)
    stdscr.addstr(sh // 2, sw // 2 - 5, "Game Over!")
    stdscr.refresh()
    time.sleep(2)

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\nGame over!")