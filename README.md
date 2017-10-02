# imageManipulationService
Image manipulation HTTP service used to store images.

Instructions for testing:

```POST /v1/image```

Upload new image. Request body should be image data.

Curl Command
```
curl -i -F file=@testingImages/signApple.jpg http://localhost:5000/v1/image
```

```GET /v1/image```

List metadata for stored images.

Curl Command
```
curl http://localhost:5000/v1/image
```

```GET /v1/image/<id>```

View metadata about image with id <id> .

Curl Command
```
curl http://localhost:5000/v1/image/1
```