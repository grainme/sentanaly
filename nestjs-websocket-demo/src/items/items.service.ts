import { Injectable, OnModuleInit } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { Item, ItemDocument } from './item.schema';
import { ItemsGateway } from './items.gateway';

@Injectable()
export class ItemsService implements OnModuleInit {
  private changeStream: any;

  constructor(
    @InjectModel(Item.name) private itemModel: Model<ItemDocument>,
    private itemsGateway: ItemsGateway,
  ) {}

  async onModuleInit() {
    // Set up the change stream
    this.changeStream = this.itemModel.watch();

    this.changeStream.on('change', async (change: any) => {
      console.log('Change detected:', change);

      switch (change.operationType) {
        case 'insert': {
          const document = change.fullDocument;
          this.itemsGateway.emitNewItem(document);
          break;
        }
        case 'update': {
          const document = await this.itemModel.findById(
            change.documentKey._id,
          );
          this.itemsGateway.emitUpdateItem(document);
          break;
        }
        case 'delete': {
          this.itemsGateway.emitDeleteItem(change.documentKey._id);
          break;
        }
      }
    });
  }

  async findAll(): Promise<Item[]> {
    return this.itemModel.find().sort({ createdAt: 1 }).exec();
  }
}
