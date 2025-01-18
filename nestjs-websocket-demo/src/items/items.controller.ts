import { Controller, Get, Post, Body } from '@nestjs/common';
import { ItemsService } from './items.service';
import { Item } from './item.schema';

@Controller('items')
export class ItemsController {
  constructor(private readonly itemsService: ItemsService) {}

  @Get()
  findAll(): Promise<Item[]> {
    return this.itemsService.findAll();
  }
}
