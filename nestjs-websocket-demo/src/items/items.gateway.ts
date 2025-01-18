import { WebSocketGateway, WebSocketServer } from '@nestjs/websockets';
import { Server } from 'socket.io';
import { Item } from './item.schema';

@WebSocketGateway({
  cors: {
    origin: ['http://localhost:5173'], // Vite's default port
    credentials: true,
  },
})
export class ItemsGateway {
  @WebSocketServer()
  server: Server;

  emitNewItem(item: Item) {
    this.server.emit('itemCreated', item);
  }

  emitUpdateItem(item: Item) {
    this.server.emit('itemUpdated', item);
  }

  emitDeleteItem(itemId: string) {
    this.server.emit('itemDeleted', itemId);
  }
}
