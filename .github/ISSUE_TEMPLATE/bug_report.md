---
name: Bug report
about: Something did not work
title: ""
labels: bug
body:
  - type: textarea
    id: what
    attributes:
      label: What happened
      description: What you did, and what you got instead.
    validations:
      required: true
  - type: textarea
    id: machine
    attributes:
      label: Your setup
      description: Blender version, operating system, and the file type of the model.
    validations:
      required: true
  - type: input
    id: model
    attributes:
      label: Model file type
      placeholder: .glb, .fbx, .blend
    validations:
      required: true
