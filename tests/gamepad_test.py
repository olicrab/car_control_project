import pygame
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

pygame.init()
pygame.joystick.init()
joystick_count = pygame.joystick.get_count()
logger.info(f"Found {joystick_count} joystick(s)")
if joystick_count == 0:
    logger.error("No joystick detected")
    exit(1)

joystick = pygame.joystick.Joystick(0)
joystick.init()
logger.info(f"Joystick: {joystick.get_name()}")

try:
    while True:
        pygame.event.pump()
        buttons = {i: joystick.get_button(i) for i in range(joystick.get_numbuttons())}
        axes = {i: joystick.get_axis(i) for i in range(joystick.get_numaxes())}
        hats = joystick.get_hat(0)
        logger.info(f"Buttons: {buttons}, Axes: {axes}, Hat: {hats}")
except KeyboardInterrupt:
    joystick.quit()
    pygame.quit()
    logger.info("Test stopped")