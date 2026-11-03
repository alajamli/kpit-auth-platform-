import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TestReportsComponent } from './test-reports.component';

describe('TestReportsComponent', () => {
  let component: TestReportsComponent;
  let fixture: ComponentFixture<TestReportsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TestReportsComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(TestReportsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
