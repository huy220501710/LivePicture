# Pinterest Clone

Vue 3 & FastAPI – A modern full-stack image-sharing platform built with Vue 3 frontend and FastAPI backend.

## Overview

### Features

- Masonry grid feed with infinite scroll  
- Search by query and tags  
- Detailed pins with comments, likes, related pins  
- Create/edit pins and boards  
- User profiles with followers/following  
- Real-time chat & notifications  
- SSE & WebSocket-powered updates  
- Smart recommendations based on user activity  
- JWT & Google OAuth2  
- REST & GraphQL APIs


## Technologies Used

### Backend  
- **FastAPI** – REST & GraphQL API  
- **SQLAlchemy** – ORM for database interactions  
- **Pydantic** – data validation & environment management  
- **JWT** – access/refresh tokens with revocation support  
- **OAuth2** – Google authentication  
- **httpx** – interaction with external APIs  
- **FastAPI-Cache** – API-level caching  
- **FastAPI-Limiter** – API-level rate limiting  
- **FastAPI-Mail** – sending emails via FastAPI  
- **GraphQL (Strawberry)** – GraphQL API layer

### Databases  
- **PostgreSQL**, **MySQL**, **MongoDB** – relational & non-relational databases  
- **Redis** – caching, token revocation, Celery broker/results, RedBeat  

### Async Tasks & Realtime  
- **Celery** – async tasks: email sending, image processing  
- **Celery Beat** – periodic tasks (e.g., promo emails)  
- **Redis Stream** – Consumer Groups, message streaming, background worker processing
- **Redis pub/sub** – message passing between Celery and FastAPI
- **RabbitMQ** – task and result passing between Celery and FastAPI
- **RabbitMQ pub/sub** – message publication to exchange, queue subscription, SSE message transfer
- **RabbitMQ stream** – message publishing and consumption from RabbitMQ queues
- **WebSockets** – real-time chat with `FastAPI.websockets`  
- **SSE (Server-Sent Events)** – real-time notifications  
- **Asyncio**, **Aiofiles** – asynchronous operations  

### Frontend  
- **Vue 3** – modern JavaScript frontend framework  
- **Pinia** – state management  
- **Vue Router** – routing  
- **Tailwind CSS** – utility-first CSS framework  
- **Axios** – HTTP client  




## Discussion  

Have suggestions or improvements? Feel free to open an issue or discussion!

## License 

MIT License – free to use & share!
