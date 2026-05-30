# ISWC 2026 demo — mgllib and data assets derived from pyvr-example:
# https://github.com/DaFluffyPotato/pyvr-example  (see credits.py)
import pygame
import sys
from input_manager import InputManager
from gesture_manager import GestureManager
from app_state_manager import AppStateManager, AppAction
from pico_sniper import PicoSniper

def main():
    pygame.init()
    
    # 800x600 window
    screen_width = 1200
    screen_height = 800
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("AR Glass Prototype")
    
    # Needs to match Unity port settings as needed, or empty for debug mode
    # Defaulting to no serial port if we just want keyboard debug
    # You can pass serial_port='/dev/tty.usbmodem...' if you have one
    # input_manager = InputManager(serial_port='/dev/cu.usbmodem11101') 
    input_manager = InputManager(port_right='/dev/cu.usbmodem11101', port_left='/dev/cu.usbmodem11201')
    gesture_manager = GestureManager(input_manager)
    app_state_manager = AppStateManager(screen, input_manager)
    
    # Wire the gesture callback to the menu
    gesture_manager.on_menu_triggered = app_state_manager.open_menu

    clock = pygame.time.Clock()
    
    running = True
    action = AppAction.NONE
    while running:
        # FPS limit
        clock.tick(60)
        
        # Event processing
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
                
        # 1. Input Processing
        input_manager.process_pygame_events(events)
        
        # 2. Gesture checking
        gesture_manager.update()
        
        # 3. State update
        app_state_manager.update()
        action = app_state_manager.pop_action()
        if action == AppAction.LAUNCH_PICO_SNIPER:
            running = False
            continue
        
        # 4. Rendering
        app_state_manager.draw()
        
        # Display flip
        pygame.display.flip()

    input_manager.stop_serial()
    app_state_manager.cleanup()
    pygame.quit()

    if action == AppAction.LAUNCH_PICO_SNIPER:
        PicoSniper().run()
    else:
        sys.exit()

if __name__ == "__main__":
    main()