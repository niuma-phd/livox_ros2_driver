cmake_minimum_required(VERSION 3.8)
project(livox_ros2_driver_bringup)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(DIRECTORY config
  DESTINATION share/${PROJECT_NAME}
)

install(FILES
  launch/horizon.launch.py
  launch/avia.launch.py
  DESTINATION share/${PROJECT_NAME}/launch
)

install(PROGRAMS
  ../scripts/configure_broadcast.py
  ../scripts/_validate_livox_topics.py
  ../scripts/validate_topics.sh
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(bringup_contract test/test_bringup_contract.py)
  ament_add_pytest_test(config_validation test/test_config_validation.py)
  ament_add_pytest_test(configure_broadcast test/test_configure_broadcast.py)
  ament_add_pytest_test(validate_livox_topics test/test_validate_livox_topics.py)
endif()

ament_package()
