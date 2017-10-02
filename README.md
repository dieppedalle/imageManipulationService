# imageManipulationService
Image manipulation HTTP service used to store images.

Instructions for testing:
```POST /v1/image```
Upload new image. Request body should be image data.

* Curl Command
```
curl -i -F file=@testingImages/signApple.jpg http://localhost:5000/v1/image
```
